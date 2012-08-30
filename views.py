#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os,sys
import tempfile2 as tempfile
import codecs
import tarfile
import cStringIO
import Image,ImageDraw

import unicodedata
from unicodedata import normalize
from datetime import datetime, date, time
from xml.dom.minidom import parse, parseString, getDOMImplementation
from django import forms

from django.core import serializers
from django.db import IntegrityError
from django.http import HttpResponse,HttpResponseNotFound, HttpResponseRedirect
from django.shortcuts import render, render_to_response
from django.template import RequestContext
from django.utils.datastructures import SortedDict


from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login,logout
from django.views.generic.simple import direct_to_template
from django.utils.encoding import smart_str

import settings
from forms.models import UnidadeSaude, Formulario, Ficha
from forms.HumanRegister import HumanRegister


def strip_accents(s):
    return ''.join((c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn'))

def smart_truncate_string(str, size):
    if len(str) < size:
        return str
    return str[:size-3].rsplit(' ', 1)[0] + ' ...'

def getText(nodelist):
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)

def smart_int(i):
    if i.isdigit():
        #It is a number
        return int(i)
    #It is a string and it wont have newline characters
    return ' '.join(i.splitlines())

class customError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def getState(cep):
    state =''
    prefixo = int(cep[0:5])
    if int(cep[0]) < 2:
        state = 'sp'
    elif prefixo >= 20000 and prefixo < 29000:
        state = 'rj'
    elif prefixo >= 29000 and prefixo < 30000:
        state = 'es'
    elif int(cep[0]) ==3:
        state = 'mg'
    elif prefixo >= 40000 and prefixo < 49000:
        state = 'ba'
    elif prefixo >= 49000 and prefixo <= 49999:
        state = 'se'
    elif prefixo >= 50000 and prefixo <= 56999:
        state = 'pe'
    elif prefixo >= 57000 and prefixo <= 57999:
        state = 'al'
    elif prefixo >= 58000 and prefixo <= 58999:
        state = 'pb'
    elif prefixo >= 59000 and prefixo <= 59999:
        state = 'rn'
    elif prefixo >= 60000 and prefixo <= 63999:
        state = 'ce'
    elif prefixo >= 64000 and prefixo <= 64999:
        state = 'pi'
    elif prefixo >= 65000 and prefixo <= 65999:
        state = 'ma'
    elif prefixo >= 66000 and prefixo <= 68899:
        state = 'pa'
    elif prefixo >= 68900 and prefixo <= 68999:
        state = 'ap'
    elif prefixo >= 69000 and prefixo <= 69299:
        state = 'am'
    elif prefixo >= 69400 and prefixo <= 69899:
        state = 'am'
    elif prefixo >= 69300 and prefixo <= 69399:
        state = 'ro'
    elif prefixo >= 69900 and prefixo <= 69999:
        state = 'ac'
    elif prefixo >= 70000 and prefixo <= 73699:
        state = 'df'
    elif prefixo >= 73700 and prefixo <= 76799:
        state = 'go'
    elif prefixo >= 76800 and prefixo <= 76999:
        state = 'rn'
    elif prefixo >= 77000 and prefixo <= 77999:
        state = 'to'
    elif int(cep[0]) ==9:
        state = 'rs'
    elif prefixo >= 78000 and prefixo <= 78899:
        state = 'mt'
    elif prefixo >= 79000 and prefixo <= 79999:
        state = 'ms'
    elif prefixo >= 80000 and prefixo <= 86999:
        state = 'pr'
    elif prefixo >= 87000 and prefixo <= 89999:
        state = 'sc'
    return state

def correct_address(request, cep):
    state = getState(cep)
    import_autocomplete = "from autocomplete.models import ruas%s as acTool"%(state,)
    exec import_autocomplete
    r = acTool.objects.filter(CEP=cep)
    if not r:
        json = "{}"
    else:
        r = r[0]
        json = """
        {
            "street"  : "%s",
            "city": "%s",
            "state": "%s"
        }
        """%(r.Logradouro + ' ' + r.Nome , r.Localidade, state.upper())
    return HttpResponse(json)

def list_forms_by_health_unit(request, healthUnit):
    if not request.user.is_authenticated():
        return HttpResponseRedirect(settings.SITE_ROOT)
    import_str = 'from forms.models import UnidadeSaude, Formulario'
    exec import_str
    us = UnidadeSaude.objects.get(id=int(healthUnit))
    form_list = Formulario.objects.filter(unidadesaude=us)
    return  render_to_response('showForms.html',
            locals(), RequestContext(request, {}))

def normalizeString(txt, codif='utf-8'):
    txt = normalize('NFKD', txt.decode(codif)).encode('ASCII','ignore')
    return txt.lower()

def createXML(keys, dictValues):
    xmlStr = u'<?xml version="1.0" encoding="utf-8"?>'
    xmlStr += u'<documento>'
    for k in keys:
        for item in dictValues.getlist(k):
            xmlStr += u'<%s>%s</%s>'%(k,item,k)
    xmlStr += u'</documento>'
    return xmlStr

def edit_form(request, fichaId, f=''):
    if not request.user.is_authenticated():
        return HttpResponseRedirect(settings.SITE_ROOT)
    import_str = 'from forms.models import Paciente, UnidadeSaude,Ficha, Formulario, HistoricoFicha'
    exec import_str
    try:
        ficha = Ficha.objects.get(pk=int(fichaId))
    except Ficha.DoesNotExist:
        url = settings.SITE_ROOT
        return render(request, 'error.html',
            dictionary=locals(), context_instance=RequestContext(request, {}), status=404)
    p = Paciente.objects.get(id=int(ficha.paciente.id))
    if request.method == 'POST':
        form = request.POST
        keys = []
        for k in form:
            if k != 'edit':
                keys.append(k)
        if len(keys) == 0:
            msg = u'Formulário sem nenhuma informação preenchida'
            url = settings.SITE_ROOT
            return render_to_response('error.html',
                locals(), RequestContext(request, {}))
        xmlStr = createXML(keys, form)
        us = request.user.get_profile().unidadesaude_favorita
        # Keep old version for logging into History table
        oldXML = ficha.conteudo
        hf = HistoricoFicha(
            ficha = ficha,
            conteudo = oldXML
        )
        hf.save()
        #Get new content
        ficha.conteudo = xmlStr
        #Save new version
        ficha.save()
        return HttpResponseRedirect(settings.SITE_ROOT)
    #else GET method
    form = Formulario.objects.get(id=int(ficha.formulario.id))
    pathname, moduleFormName = os.path.split(form.path)
    pathname ='%s/'%(pathname,)
    if not pathname in sys.path:
        sys.path.append(pathname)
    try:
        moduleForm = __import__(moduleFormName)
    except ImportError:
        msg = 'Módulo não encontrado'
        url = settings.SITE_ROOT
        return render(request, 'error.html',
            dictionary=locals(), context_instance=RequestContext(request, {}), status=404)

    return moduleForm.handle_request(request, f)

def getFieldsXML(form):
    #return DOM object for a xml setting file of a form
    pathname, moduleFormName = os.path.split(form.path)
    pathname ='%s/'%(pathname,)
    if not pathname in sys.path:
        sys.path.append(pathname)
    try:
        moduleForm = __import__(moduleFormName)
        xmlPath = '%s/%s/%s'%(pathname,moduleFormName,
                moduleForm.fields_xml_path,)
        xmlDom = parse(xmlPath)
    except ImportError:
        raise customError('Módulo não encontrado')
    except IOError:
        return None
    except AttributeError:
        return None
    return xmlDom

def getOrderedFields(form, show_form=False, number_multifields=4, form_in_index=False):
    xmlDOM= getFieldsXML(form)
    if xmlDOM:
        elements = xmlDOM.getElementsByTagName('fields')[0].childNodes
        content = SortedDict(
            [(el.nodeName, getText(el.childNodes)) for el in elements
            if el.nodeType == el.ELEMENT_NODE]
        )
        content = SortedDict()
        elements = xmlDOM.firstChild.childNodes
        for el in elements:
            if el.nodeName == "multipleFields":
                fieldsetName = el.getAttribute('fieldset')
                for idx in range(1, number_multifields):
                    for m_el in el.childNodes:
                        if m_el.nodeType == m_el.ELEMENT_NODE:
                            if show_form:
                                content["%s - %s_%d"%(form.tipo.nome, m_el.nodeName, idx)] = \
                                    "%s %s %d"%(getText(m_el.childNodes),
                                    fieldsetName, idx)
                            else:
                                content["%s_%d"%(m_el.nodeName, idx)] = \
                                    "%s %s %d"%(getText(m_el.childNodes),
                                    fieldsetName, idx)
            else:
                if el.nodeType == el.ELEMENT_NODE:
                    if show_form:
                    	if form_in_index:
                        	content["%s - %s" % (form.tipo.nome, el.nodeName)] = "%s - %s"%(form.tipo.nome, getText(el.childNodes))
                    	else:
                        	content[el.nodeName] = "%s - %s"%(form.tipo.nome, getText(el.childNodes))
                    else:
                        content[el.nodeName] = getText(el.childNodes)

        return content
    return {}

def showFieldsXML(request, formId):
    try:
        form = Formulario.objects.get(id=int(formId))
        xmlDOM= getFieldsXML(form)
        return HttpResponse(xmlDOM.toxml(), mimetype='application/xml')
    except Formulario.DoesNotExist:
        msg = 'Formulário Inexistente'
        url = settings.SITE_ROOT
        return render(request, 'error.html',
            dictionary=locals(), context_instance=RequestContext(request, {}), status=404)
    except AttributeError:
        msg = 'XML não encontrado'
        url = settings.SITE_ROOT
        return render(request, 'error.html',
            dictionary=locals(), context_instance=RequestContext(request, {}), status=404)

def handle_form(request, formId, patientId, f=''):
    if not request.user.is_authenticated():
        return HttpResponseRedirect(settings.SITE_ROOT)
    import_str = 'from forms.models import Paciente, UnidadeSaude,Ficha, Formulario, HistoricoFicha'
    exec import_str
    if request.method == 'POST':
        form = request.POST
        if int(patientId) == 0: # new patient
            nome = form['nome']
            nome_mae = form['nome_mae']
            data_nascimento = form['data_nascimento']
            new_patient = Paciente(
                nome=nome,
                nome_mae = nome_mae,
                data_nascimento=data_nascimento
            )
            try:
                new_patient.save()
            except IntegrityError:
                msg = 'Paciente já existente no sistema'
                url = settings.SITE_ROOT
                return render(request, 'error.html',
                    dictionary=locals(),
                    context_instance=RequestContext(request, {}),
                    status=404)
            p = new_patient
        else:
            p = Paciente.objects.get(id=int(patientId))
        keys = []
        for k in form:
            if k != 'edit':
                keys.append(k)
        # Protection for empty submissions
        if not len(keys):
            return HttpResponseNotFound(u'Formulário submetido vazio')
        xmlStr = createXML(keys, form)
        us = request.user.get_profile().unidadesaude_favorita
        if 'edit' in form.keys():
            newFicha = Ficha.objects.get(pk=int(form['edit']))
            oldXML = newFicha.conteudo
            hf = HistoricoFicha(
                ficha = newFicha,
                conteudo = oldXML
            )
            hf.save()
            newFicha.conteudo = xmlStr
            newFicha.unidadesaude = xmlStr
        else:#New Entry
            f = Formulario.objects.get(id=int(formId))
            newFicha = Ficha(
                paciente   = p,
                formulario = f,
                unidadesaude = us,
                conteudo   = xmlStr
            )
        # For sharing info from a portable device to the server
        if not settings.SERVER_VERSION:
            f = Formulario.objects.get(id=int(formId))
            tmp_file = tempfile.NamedTemporaryFile(
                suffix='.info',
                prefix='ficha',
                dir=settings.COMM_DIR,
            )
            #Workaround for open a utf-8 file
            info_filename = tmp_file.name
            tmp_file.close()
            info_file = codecs.open(info_filename, 'w', encoding='utf-8')
            info_file.write(p.nome + '\n')
            info_file.write(p.data_nascimento + '\n' )
            info_file.write(p.nome_mae+ '\n')
            info_file.write(f.nome + '\n')
            info_file.write(f.tipo.nome + '\n')
            info_file.write(us.nome + '\n')
            if 'edit' in form.keys():
                info_file.write('edit')
            xml_file = codecs.open(info_file.name.replace('.info', '.xml'), 'w',encoding='utf-8')
            xml_file.write(xmlStr)
            info_file.close()
            xml_file.close()

        newFicha.save()
        return HttpResponseRedirect(settings.SITE_ROOT)
    # else METHOD == GET
    form = Formulario.objects.get(id=int(formId))
    pathname, moduleFormName = os.path.split(form.path)
    pathname ='%s/'%(pathname,)
    if not pathname in sys.path:
        sys.path.append(pathname)
    try:
        moduleForm = __import__(moduleFormName)
    except ImportError:
        msg = 'Módulo não encontrado'
        url = settings.SITE_ROOT
        return render(request, 'error.html',
            dictionary=locals(),
            context_instance=RequestContext(request, {}),
            status=404)
    return moduleForm.handle_request(request, f)

def select_unidade_saude(request):
    import_str = "from forms.models import UnidadeSaude"
    exec import_str
    if request.method == 'POST':
        usId = request.POST['usId']
        if request.user.is_authenticated():
            try:
                us = UnidadeSaude.objects.get(id=int(usId))
                user = request.user.get_profile()
                user.unidadesaude_favorita = us
                user.save()
            except UnidadeSaude.DoesNotExist:
                return HttpResponseNotFound(u'Unidade Saúde não existente')
            return HttpResponse('OK')
        return HttpResponse('Usuário não autenticado')
    return HttpResponse('Nothing to do %s'%request.method)


def jsFunctionCreateHeaderFooter(request):
    data_dict = {
        'MEDIA_URL': settings.MEDIA_URL,
        'url': settings.SITE_ROOT,
        'user': request.user,
    }
    return render_to_response('createHeaderFooter.js',
        data_dict, mimetype='application/x-javascript')

def homepage_view(request):
    import_str = "from forms.models import UnidadeSaude, tipoFormulario, Formulario, Grupo, Grupo_Formulario, UserProfile"
    exec import_str
    if request.user.is_authenticated():
        us_favorite = None
        groups = Grupo.objects.filter(membros=request.user)
        try:
            us_favorite = request.user.get_profile().unidadesaude_favorita
            if not us_favorite: #User did not belong to a group
                # Check whether now he belongs to one and set a favorite US
                if groups.count():
                    us_favorite= groups[0].unidadesaude
                    profile = request.user.get_profile()
                    profile.unidadesaude_favorita = us_favorite
                    profile.save()
        except UserProfile.DoesNotExist: #Profile was not created yet
            if groups.count():
                us_favorite= groups[0].unidadesaude
            if us_favorite:
                profile = UserProfile(unidadesaude_favorita= us_favorite, user=request.user)
            else:
                profile = UserProfile(user=request.user)
            profile.save()
        ft = tipoFormulario.objects.get(nome='Triagem')
        temp = Formulario.objects.filter(tipo=ft)
        # Remove forms that the user does not have permission
        if groups.count():
            gf = Grupo_Formulario.objects.filter(grupo__in=groups).filter(formulario__in = temp).filter(permissao='T')
            triagem_form_list = [Formulario.objects.get(pk=g['formulario'])  for g in gf.values('formulario').distinct()]
        else: #User does not belong to any group, so do not access any form
            triagem_form_list = Formulario.objects.none()
        del temp
        unidades_saudes = [g.unidadesaude for g in groups]
    url = settings.SITE_ROOT
    return render_to_response('homepage_template.html',
            locals(), RequestContext(request, {}))

def getPatientList(us):
    import_str = 'from forms.models import Paciente, Ficha, Formulario, Grupo, Grupo_Formulario'
    exec import_str
    patient_list = []
    fichas = Ficha.objects.filter(formulario__tipo__nome='Triagem').filter(unidadesaude__in = us)
    if fichas:
        for f in fichas:
            patient_list.append(f.paciente)
    return patient_list

def getFilledFormsId(patient):
    import_str = 'from forms.models import Paciente, Ficha, Formulario'
    exec import_str
    retList = []
    fichas = Ficha.objects.select_related().filter(paciente=patient)
    retList = [ f.formulario.id for f in fichas]
    return retList

def getListOfUS(user):
    import_str = 'from forms.models import UnidadeSaude, Grupo, Grupo_Formulario'
    exec import_str
    groups       = Grupo.objects.filter(membros=user)
    us_list = []
    for gr in groups:
        #Get "Unidade de Saudes" that the user's groups belong to.
        us_list.append(gr.unidadesaude)
    #Get "Unidade de Saude" related to the user's defined
    for us in us_list:
        for us2 in us.relacionamento.all():
            if us2 not in us_list:
                us_list.append(us2)
    return us_list

def getUSfromTriagem(patient):
    import_str = 'from forms.models import Paciente, UnidadeSaude,Ficha'
    exec import_str
    return Ficha.objects.filter(paciente=patient).get(formulario__tipo__nome='Triagem').unidadesaude

def formOrderList(usr):
    import_str = 'from forms.models import Grupo_Formulario, Grupo, Formulario'
    exec import_str
    groups = Grupo.objects.filter(membros=usr)
    forms  = []
    formsOrder = ['Triagem', 'Consulta', 'Exames', 'Follow-up']
    for t in formsOrder:
        forms.extend(
            Grupo_Formulario.objects.filter(formulario__tipo__nome=t).filter(grupo__in = groups)\
                .values_list('formulario', flat=True).distinct()
            )
    form_list =[]
    for id in forms:
        form_list.append(Formulario.objects.get(pk=id))
    return form_list

def retrieveUnidadesSaude(request):
    if not request.user.is_authenticated():
        return HttpResponseRedirect(settings.SITE_ROOT)
    import_str = 'from forms.models import UnidadeSaude'
    exec import_str

    unidades = UnidadeSaude.objects.all()

    data = serializers.serialize('json', unidades, fields=('nome', 'cidade', 'UF'))
    return HttpResponse(data, mimetype='application/json')


def show_patients(request):
    if not request.user.is_authenticated():
        return HttpResponseRedirect(settings.SITE_ROOT)
    import_str = 'from forms.models import Paciente, UnidadeSaude,Ficha, Formulario, Grupo, Grupo_Formulario'
    exec import_str
    MEDIA = 'custom-media/'
    us_list =  getListOfUS(request.user)
    groups       = Grupo.objects.filter(membros=request.user)
    group_names = [g.nome for g in groups]
    forms_list = formOrderList(request.user)
    forms_list2 = [
        Formulario.objects.get(pk=dictFormId.values()[0])
        for dictFormId in Grupo_Formulario.objects.filter(grupo__in = groups)\
        .values('formulario').distinct()
    ]
    patient_list = getPatientList(us_list)
    patient_fichas = {}
    patient_us     = {}
    for p in patient_list:
        patient_fichas[p.id] = getFilledFormsId(p)
        patient_us[p.id] = getUSfromTriagem(p)
    url = settings.SITE_ROOT
    return render_to_response('show.Patients.html',
            locals(), RequestContext(request, {}))

def list_patients(request):
    if not request.user.is_authenticated():
        return HttpResponseRedirect(settings.SITE_ROOT)
    import_str = 'from forms.models import Paciente, UnidadeSaude, Grupo'
    exec import_str
    us_list =  getListOfUS(request.user)
    patient_list = getPatientList(us_list)
    return render_to_response('list.Patients.html',
            locals(), RequestContext(request, {}))

def sapem_login(request):
    url = settings.SITE_ROOT
    if request.method == 'POST':
        user = authenticate(username=request.POST['username'], password=request.POST['password'])
        if user is not None:
            if user.is_active:
                login(request, user)
                return HttpResponseRedirect(url)
            msg = u'Conta Inativa. Contate o administrador do sistema.'
            return render(request, 'error.html',
                dictionary=locals(),
                context_instance=RequestContext(request, {}),
                status=404)
        msg = u'Usuário e/ou senha inválida'
    return render_to_response('homepage_template.html',
        locals(), RequestContext(request, {}))

def sapem_logout(request):
    logout(request)
    return HttpResponseRedirect(settings.SITE_ROOT)

def retrieveFichas(patientId, formType=''):
    import_str = 'from forms.models import Paciente, UnidadeSaude,Ficha, Formulario, tipoFormulario'
    exec import_str
    register_list =[]
    try:
        patient = Paciente.objects.get(id=patientId)
    except Paciente.DoesNotExist:
        register_list.append("<?xml version='1.0' encoding='UTF-8' ?><error>Paciente não encontrado</error>")
        return register_list
    register_qs = Ficha.objects.filter(paciente=patient)
    if formType != '':
        try:
            t = tipoFormulario.objects.get(nome=formType)
        except tipoFormulario.DoesNotExist:
            raise customError('Esse tipo de formulário não existe.')
        register_qs = register_qs.filter(formulario__tipo=t)
    if not register_qs:
        raise customError('A busca não retornou resultados')
    return register_qs

def retrieveHumanRegister(patientId, form_type=None):
    import_str = 'from forms.models import Paciente, Ficha,tipoFormulario'
    exec import_str
    if form_type:
        hRegDict ={ form_type: [HumanRegister(r, getOrderedFields(r.formulario))
                for r in retrieveFichas(int(patientId), form_type)]}
    else:
        p = Paciente.objects.get(id=patientId)
        form_types = [ficha.formulario.tipo
            for ficha in Ficha.objects.filter(paciente=p)
            ]
        forms= Ficha.objects.filter(paciente=p).values('formulario')
        hRegDict = {}
        for form_type in form_types:
            hRegDict[form_type] = [HumanRegister(r, getOrderedFields(r.formulario))
                    for r in retrieveFichas(int(patientId), form_type)]
    return hRegDict

def showPatientLastRegister(request,patientId, formId):
    if not request.user.is_authenticated():
        return HttpResponseRedirect(settings.SITE_ROOT)
    import_str = 'from forms.models import Paciente, UnidadeSaude,Ficha, Formulario'
    exec import_str
    try:
        form = Formulario.objects.get(id=formId)
        try:
            #Add Ficha id dinamically
            impl = getDOMImplementation()
            try:
                ficha = retrieveFichas(int(patientId), form.tipo).latest('data_ultima_modificacao')
            except AttributeError:
                return HttpResponseNotFound('A busca não retornou resultados')
            if isinstance(ficha, str):#Is
                return HttpResponse(ficha)
            dom = parseString(ficha.conteudo.encode('utf-8'))
            tag = dom.createElement('ficha_id')
            id_txt = dom.createTextNode('%i'%ficha.id)
            tag.appendChild(id_txt)
            dom.childNodes[-1].appendChild(tag)
            xml = dom.toxml('UTF-8')
        except customError, e:
            msg = e.value
            if request.method == 'GET':
                url = settings.SITE_ROOT
                return render(request, 'error.html',
                    dictionary=locals(),
                    context_instance=RequestContext(request, {}),
                    status=404)
            return HttpResponseNotFound('A busca não retornou resultados')
    except Formulario.DoesNotExist:
        xml = "<?xml version='1.0' encoding='UTF-8' ?><error>Formulario não achado</error>"
    return HttpResponse(xml)

def showPatientAllRegisters(request,patientId):
    if not request.user.is_authenticated():
        return HttpResponseRedirect(settings.SITE_ROOT)
    import_str = 'from forms.models import Paciente, UnidadeSaude,Ficha, Formulario, Grupo, Grupo_Formulario'
    exec import_str
    try:
        registers = retrieveHumanRegister(int(patientId))
    except customError, e:
        msg = e.value
        if request.method == 'GET':
            url = settings.SITE_ROOT
            return render_to_response('error.html',
                locals(), RequestContext(request, {}))
        return HttpResponseNotFound('A busca não retornou resultados')
    patient = Paciente.objects.get(id=int(patientId))
    #Check groups rights
    groups       = Grupo.objects.filter(membros=request.user)
    us_list =  getListOfUS(request.user)
    gf = Grupo_Formulario.objects.filter(grupo__in = groups)
    if not len(gf):
        return HttpResponseNotFound('A busca não retornou resultados')
    # Ugly fix. TODO check if this is valid for all situations.
    gf = gf[0]
    url = settings.SITE_ROOT
    return render_to_response('show.registers.patient.html',
        locals(), RequestContext(request, {}))


def showPatientRegisters(request,patientId, formId):
    if not request.user.is_authenticated():
        return HttpResponseRedirect(settings.SITE_ROOT)
    import_str = 'from forms.models import Paciente, UnidadeSaude,Ficha, Formulario, Grupo, Grupo_Formulario'
    exec import_str
    form = Formulario.objects.get(id=formId)
    try:
        registers = retrieveHumanRegister(int(patientId), form.tipo)\
            .values()[0]
    except customError, e:
        msg = e.value
        if request.method == 'GET':
            url = settings.SITE_ROOT
            return render_to_response('error.html',
                locals(), RequestContext(request, {}))
        return HttpResponseNotFound('A busca não retornou resultados')
    patient = Paciente.objects.get(id=int(patientId))
    #Check groups rights
    groups       = Grupo.objects.filter(membros=request.user)
    us_list =  getListOfUS(request.user)
    gf = Grupo_Formulario.objects.filter(grupo__in = groups).filter(formulario= form)
    if not len(gf):
        return HttpResponseNotFound('A busca não retornou resultados')
    # Ugly fix. TODO check if this is valid for all situations.
    gf = gf[0]
    url = settings.SITE_ROOT
    return render_to_response('show.registers.html',
        locals(), RequestContext(request, {}))

def showFichaConteudo(request, fichaId):
    if not request.user.is_authenticated():
        return HttpResponseRedirect(settings.SITE_ROOT)
    import_str = 'from forms.models import Ficha'
    exec import_str
    ficha = Ficha.objects.get(pk=int(fichaId))
    xmlStr = ficha.conteudo
    url = settings.SITE_ROOT
    return HttpResponse( xmlStr, mimetype="application/xhtml+xml")

def retrieveTriagemName(request, patientId):
    import_str = 'from forms.models import Paciente, Ficha, Formulario, tipoFormulario'
    exec import_str
    patient  = Paciente.objects.get(pk=int(patientId))
    ficha_qs = Ficha.objects.filter(paciente=patient)
    tTriagem = tipoFormulario.objects.get(nome='Triagem')
    triagem = ficha_qs.filter(formulario__tipo=tTriagem)[0] # There is only one Triagem report
    return HttpResponse(triagem.formulario.nome)

def retrieveUS(request, opt):
    if not request.user.is_authenticated():
        return HttpResponseRedirect(settings.SITE_ROOT)
    import_str = 'from forms.models import UserProfile'
    exec import_str
    user = UserProfile.objects.get(user=request.user)
    if opt == 'name':
        return  HttpResponse(user.unidadesaude_favorita.nome)
    return HttpResponseNotFound('A busca não retornou resultados')

def retrieveLastReportByType(request, patientId, type):
    if not request.user.is_authenticated():
        return HttpResponseRedirect(settings.SITE_ROOT)
    import_str = 'from forms.models import Paciente, Ficha, Formulario, tipoFormulario'
    exec import_str
    try:
        ficha = retrieveFichas(patientId, type).latest('data_ultima_modificacao')
    except customError, e:
        msg = e.value
        if request.method == 'GET':
            url = settings.SITE_ROOT
            return render_to_response('error.html',
                locals(), RequestContext(request, {}))
        return HttpResponseNotFound('A busca não retornou resultados')
    return HttpResponse( ficha.conteudo, mimetype="application/xhtml+xml")

def xls_to_response(xls, fname):
    response = HttpResponse(mimetype="application/ms-excel")
    response['Content-Disposition'] = 'attachment; filename=%s' % fname
    xls.save(response)
    return response

def csv_to_response(csvObj, fname):
    import csv
    response = HttpResponse(mimetype="text/csv")
    response['Content-Disposition'] = 'attachment; filename=%s' % fname
    writer = csv.writer(response)
    for l in csvObj:
        writer.writerow(l)
    return response

def zip_to_response(files, fname):
    import zipfile
    from StringIO import StringIO
    response = HttpResponse(mimetype="application/x-zip-compressed")
    response['Content-Disposition'] = 'attachment; filename=%s' % fname
    buffer = StringIO()
    zip = zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED)
    for name in files:
        zip.write(name)
    zip.close()
    buffer.flush()
    ret_zip = buffer.getvalue()
    response.write(ret_zip)
    buffer.close()
    return response

def db2file(request, format='excel'):
    from forms.models import Ficha, Formulario,Paciente
    # Create file-like object
    # Get Fichas grouped by Formularios
    forms = Formulario.objects.all()
    fichas = Ficha.objects.all()
    if format=='excel':
        import xlwt
        wb = xlwt.Workbook(encoding='utf-8')
        # Default styles
        BG0 = xlwt.Pattern()
        BG0.pattern = BG0.SOLID_PATTERN
        BG0.pattern_fore_colour = 22
        BG1 = xlwt.Pattern()
        BG1.pattern = BG1.SOLID_PATTERN
        BG1.pattern_fore_colour = 47
        font0 = xlwt.Font()
        font0.name = 'Arial'
        font0.bold = True
        font1 = xlwt.Font()
        font1.name = 'Arial'
        header_style = xlwt.XFStyle()
        header_style.font = font0
        header_style.pattern = BG0
        body_style = xlwt.XFStyle()
        body_style.font = font1
        body_style.pattern = BG1

        for f in forms:
            # Tip: Excel just allows sheet names up to 31 caracters
            ws = wb.add_sheet(smart_truncate_string(f.nome, 31))
            ws.write(0, 0, u"Nome do paciente", header_style )
            ws.write(0, 1, u"Data de nascimento",header_style )
            ws.write(0, 2, u"Nome da mãe",header_style)
            ws.write(0, 3, u"Unidade de saúde",header_style)
            orderedFields = getOrderedFields(f)
            for idx, labels in enumerate(orderedFields.values()):
                ws.write(0, idx+4, labels  ,header_style)
            headers = SortedDict([ (k,i+4) for i, k in enumerate(orderedFields.keys())])
            ws.col(0).width = 9000
            ws.col(1).width = 5000
            ws.col(2).width = 9000
            ws.col(3).width = 12000
            index = 4
            for row, ficha in enumerate(fichas.filter(formulario=f)):
                ws.write(row+1,0,ficha.paciente.nome)
                ws.write(row+1,1,ficha.paciente.data_nascimento)
                ws.write(row+1,2, ficha.paciente.nome_mae)
                ws.write(row+1,3,ficha.unidadesaude.nome)
                # Parse ficha
                xml = parseString(ficha.conteudo.encode("utf-8" ))
                for field in xml.firstChild.childNodes:
                    try:
                        ws.write(
                        row+1,headers[field.tagName],
                        ', '.join(["%s"%(smart_int(f.firstChild.nodeValue))
                            for f in xml.getElementsByTagName(field.tagName)]))
                    except:
                        pass
        return xls_to_response(wb, 'pacientes.xls')
    if format=='csv':
        import csv, random
        import string
        valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
        #Generate a file for each Triagem and complete with the other forms
        fields = []
        files = []
        triagens = Formulario.objects.filter(tipo__nome= 'Triagem')
        other_forms_fields = SortedDict()
        for f_type in ['Consulta', 'Exames', 'Follow-up']:
            other_forms = Formulario.objects.filter(tipo__nome=f_type)
            for f in other_forms:
                other_forms_fields[f.id] = getOrderedFields(f, show_form=True, form_in_index=True)
        for tForm in triagens:
            form_fields = SortedDict()
            form_fields[tForm.id] = getOrderedFields(tForm, show_form=True, form_in_index=True)
            form_fields.update(other_forms_fields)
            csvfilename = '%s_%04d.csv'%(
                tForm.nome.replace(' ', '_').lower().encode('utf-8'),
                random.randint(1, 9999)
                )
            csvfilename =  '/tmp/%s'%''.join(c for c in csvfilename if c in valid_chars)

            csvfile = open(csvfilename, 'wb')
            files.append(csvfilename)
            writer = csv.writer(csvfile, delimiter=';', quotechar='"', quoting=csv.QUOTE_ALL)
            #header
            headerList = [v.encode('utf-8') for set_v in form_fields.values() for v in set_v.values()]
            headerKeysList = [v.encode('utf-8') for set_v in form_fields.values() for v in set_v.keys()]
            writer.writerow(headerList)
            # O SPSS corta valores das variaveis loucamente
            # por isso essa linha eh necessaria, para forçar o tamanho da coluna
            fake_line = ['-'*200] * len(headerList)
            writer.writerow(fake_line)
            # Linha com o nome das variaveis no XML
            writer.writerow(headerKeysList)
            #content
            fichas_triagem = Ficha.objects.filter(formulario=tForm)
            #Quem sao os pacientes
            data = {}.fromkeys([int(p) for p in fichas_triagem.values_list('paciente', flat=True)])
            for p in data.iterkeys():#loop over patients
                data[p] = SortedDict()
                for dict_keys in form_fields.values():
                    for k in dict_keys.keys():
                        data[p][k.encode('utf-8')] = ''
            pacientes = data.keys()
            #Todas as fichas destes pacientes
            #pacintes serao reagrupados em subconjuntos para nao exceder o numero de variaveis
            #Esta eh uma limitacao SQLite3
            num = 500
            for sub_pacientes in [pacientes[i::num] for i in range(num)]:
                fichas = Ficha.objects.filter(paciente__in=sub_pacientes)
                for ficha in fichas:
                    xml = parseString(ficha.conteudo.encode("utf-8" ))
                    paciente = ficha.paciente.id
                    for field in xml.firstChild.childNodes:
                        try:
                            field_data = ', '.join(["%s"%(smart_int(f.firstChild.nodeValue))  for f in xml.getElementsByTagName(field.tagName)])
                            data[paciente]["%s - %s" % (ficha.formulario.tipo.nome, field.tagName)] = field_data
                        except:
                            pass
            for id, tags in data.iteritems():
                tags['Triagem - data_consulta'] = str_to_date(tags['Triagem - data_consulta'])
                writer.writerow([tags[tag].encode('utf-8') for tag  in headerKeysList])
                #writer.writerow([k for k in tags.iterkeys()])
            csvfile.close()
        if request.GET.get('report', '') == "true":
            reportfilename =  '/tmp/report.txt'
            files.append(reportfilename)
            report = open(reportfilename, 'w')
            validate_export(files, report)
            report.close()
        return zip_to_response(files, 'pacientes.zip')
    return HttpResponseNotFound("File format not found")

def validate_export(files, report):
	'''
	Para cada CSV checa se os dados estao de acordo
	com os dados presentes no BD
	'''
	import csv
	from forms.models import Paciente

	# Valida cada CSV
	for f in files:

		# Ignora o report
		if 'report' in f: continue

		# Abre o CSV para leitura
		csvfile = open(f, 'rb')
		reader = csv.reader(csvfile, delimiter=';', quotechar='"', quoting=csv.QUOTE_ALL)

		# Começa o report
		report.write("%s\n" % ("-"*100))
		report.write("Verificando arquivo %s\n\n" % f)

		# Declara as variaveis
		name_index, name_mae_index, data_nascimento_index, to_be_ignored, unidade_index = None, None, None, None, None
		xml_vars = None
		header = None
		erros, pacientes_nao_encontrados, pacientes_duplicados, p_com_fichas_duplicadas = 0, 0, 0, 0

		# Para cada linha no CSV
		for index, row in enumerate(reader):

			# Salva o header e continua
			if index == 0:
				header = row
				continue

			# Ignora a fake line
			if index == 1: continue

			# Nome das variaveis
			# Salva e identifica as variaveis que vao buscar o paciente: nome, nome da mae e data de nascimento
			# Salva o index da data de consulta, que foi tratada para ficar diferente da presente no BD, e sera
			#ignorada
			if index == 2:

				xml_vars = row

				for column in row:
					original_column = column
					column = smart_str(column).strip()
					if column.startswith("Triagem") and column.endswith("nome"):
						name_index = row.index(original_column)
					if column.startswith("Triagem") and column.endswith("nome_mae"):
						name_mae_index = row.index(original_column)
					if column.startswith("Triagem") and column.endswith("data_nascimento"):
						data_nascimento_index = row.index(original_column)
					if column.startswith("Triagem") and column.endswith("data_consulta"):
						to_be_ignored = row.index(original_column)
					if column.startswith("Triagem") and column.endswith("unidade"):
						unidade_index = row.index(original_column)

				continue

			report.write("Paciente %s -  %s\n" % (smart_str(row[name_index]), smart_str(row[unidade_index])))

			# Pega as fichas do paciente
			try:
				paciente = Paciente.objects.get(nome=smart_str(row[name_index]), nome_mae=smart_str(row[name_mae_index]), data_nascimento=smart_str(row[data_nascimento_index]))
			# Caso ele nao exista
			except Paciente.DoesNotExist:
				pacientes_nao_encontrados += 1
				report.write("Nome da mae: %s\n" % smart_str(row[name_mae_index]))
				report.write("Data de nascimento: %s\n" % smart_str(row[data_nascimento_index]))
				report.write("Paciente nao encontrado!\n\n")
				continue
			# Caso exista pacientes duplicados
			except Paciente.MultipleObjectsReturned:
				pacientes_duplicados += 1
				report.write("Paciente duplicado!\n\n")
				continue

			# Monta 3 listas: com as fichas, com o conteudo das fichas e com os tipos das fichas
			# Depois 2 com as unidades de saude e com o nome das unidades
			fichas = paciente.ficha_set.all()
			fichas_xml = [parseString(smart_str(ficha.conteudo)) for ficha in fichas]
			tipo_fichas = [ficha.formulario.tipo.nome for ficha in fichas]
			unidades_nomes = [smart_str(f.unidadesaude.nome) for f in fichas]
			unidades = [f.unidadesaude.id for f in fichas]

			# Compara o nome do paciente no XML e na tabela Paciente do BD
			triagem_index = tipo_fichas.index('Triagem')
			triagem_xml = fichas_xml[triagem_index]
			triagem_nome = None
			if triagem_xml and triagem_xml.getElementsByTagName("nome"):
				triagem_nome = smart_str(triagem_xml.getElementsByTagName("nome")[0].firstChild.nodeValue)
			if triagem_nome != row[name_index]:
				report.write("Nome do paciente inconsistente no XML e no BD!\n")
				report.write("XML: %s!\n" % row[name_index])
				report.write("BD: %s\n\n" % triagem_nome)

			# Verifica se todos os formulario pertencem as mesmas unidades de saude
			if unidades and len(set(unidades)) != 1:

				report.write("Formularios em unidades distintas\n")
				report.write("Formularios: %s\n" % str([smart_str(f.formulario.nome) for f in fichas]))
				report.write("Unidades: %s\n\n" % str(unidades_nomes))

			# Verifica coluna a coluna
			for i, column in enumerate(row):

				# Ignora a data da consulta
				if i == to_be_ignored: continue

				# Pega o tipo da ficha e o nome da variavel no XML atraves da linha que
				# foi adicionada para esse proposito
				xml_var_complete = smart_str(xml_vars[i]).strip().split("-")
				tipo_da_ficha = xml_var_complete[0].strip()
				xml_var = xml_var_complete[1].strip()

				# Se o paciente nao tiver a ficha
				try:
					ficha_xml = fichas_xml[tipo_fichas.index(tipo_da_ficha)]
				except ValueError:
					continue

				# Pega o valor do BD
				try:
					field_data = ', '.join(["%s"%(smart_int(field.firstChild.nodeValue)) for field in ficha_xml.getElementsByTagName(xml_var)])
				except AttributeError:
					field_data = ''

				# Converte tudo para smart string
				column = smart_str(column)
				field_data = smart_str(field_data)

				# Compara os valores
				if column != field_data:
					erros += 1
					report.write("Erro no campo %s\n" % smart_str(header[i]))
					report.write("Valor no CSV: %s\n" % smart_str(column))
					report.write("Valor no BD: %s\n\n" % smart_str(field_data))

			# Caso existam fichas duplicadas, escreve no relatorio
			if len(tipo_fichas) != len(set(tipo_fichas)):
				p_com_fichas_duplicadas +=1
				report.write("Formularios duplicados: %s\n" % str(tipo_fichas))

			report.write("\n")

		# Relatorio final para cada arquivo
		report.write("%s pacientes verificados\n" % str(index+1-3))
		report.write("%s pacientes duplicados\n" % str(pacientes_duplicados))
		report.write("%s pacientes com fichas duplicadss\n" % str(p_com_fichas_duplicadas))
		report.write("%s pacientes nao encontrados\n" % str(pacientes_nao_encontrados))
		report.write("%s erros\n" % str(erros))
		report.write("%s\n" % ("-"*100))
		csvfile.close()


def parse_date(date):
	'''
	Aceita datas no formato DD de MES de AAAA
	'''

	meses = ['Janeiro', 'Fevereiro', 'Marco',
			'Abril', 'Maio', 'Junho', 'Julho',
			'Agosto', 'Setembro', 'Outubro',
			'Novembro', 'Dezembro']
	date_list = date.split(' de ')
	return '%s/%s/%s' % (date_list[0], meses.index(date_list[1]) + 1, date_list[2])

def str_to_date(date):
	'''
	Sao dois formatos de datas que temos nos csv
	que tem que ser transformados para DD/MM/AAAA:
	Segunda-feira, 11 de Abril de 2011
	e
	01 de Abril de 2011
	'''
	if not date: return date
	date = strip_accents(date)
	date_list = date.split(',')
	return parse_date(date_list[-1].strip())

def art_view (request, formId, patientId):
    if not request.user.is_authenticated():
        return HttpResponseRedirect(settings.SITE_ROOT)
    import_str = 'from forms.models import Paciente, UnidadeSaude,Ficha, Formulario, Grupo, Grupo_Formulario'
    exec import_str
    ficha = Ficha.objects.filter(paciente__id = patientId).filter(formulario__tipo__nome='Triagem')[0]
    if int(formId) != int(ficha.formulario.id):
        return HttpResponseNotFound(u'O formulário requisitado é invalido para esse paciente.')

    xmlContent = ficha.conteudo

    #from xml dict
    doc = parseString(xmlContent.encode('utf-8'))

    nodes = doc.firstChild.childNodes
    dictValues = {}

    for node in nodes:
        if node.firstChild:
            dictValues[node.nodeName] = node.firstChild.nodeValue

    #Translate input tags
    fields = (
        'idade',
        'tosse',
        'hemoptoico',
        'sudorese',
        'febre',
        'emagrecimento',
        'dispneia',
        'emagrecimento',
        'fumante',
        'TBXPulmonar',
        'internacaoHospitalar',
        'sida'
    )
    values = []
    for f in fields:
        try:
            value = dictValues[f]
            if f == 'idade':
                values.append(int(value))
            elif value == 'nao':
                values.append(-1)
            elif value == 'jamais':
                values.append(-1)
            elif value == 'sim':
                values.append(1)
            else:
                values.append(0)
        except:
            values.append(0)
    from art import ART
    import numpy as np
    art = ART(np.array(values, float), config_file='%s/art_conf.npz'%os.path.dirname(os.path.realpath(__file__)))
    art.net()
    index, r, R = art.getOutput()
    img = Image.new("RGB", (210,730), "#FFFFFF")
    draw = ImageDraw.Draw(img)
    colorON = ['green', 'yellow', 'red']
    color   = ['#98FB98','#EEE8AA','#CD9B9B']
    if index != None:
        color[index] = colorON[index]
    for k in range(3):
        draw.ellipse((0, k*210, 200, k*210 + 200), fill=color[k], outline=color[k])
        draw.point((100, 100+210*k), fill='black')
    if r:
        ri = 100*r/R
    draw.arc((100-ri,(index*210) + 100 -ri ,100+ri ,index*210 + 100 + ri), 0, 360, fill='black')
    f = cStringIO.StringIO()
    img.save(f, "PNG")
    f.seek(0)
    return HttpResponse (f.read(),mimetype='image/png' )


def showARTResult(request,patientId, formId):
    if not request.user.is_authenticated():
        return HttpResponseRedirect(settings.SITE_ROOT)
    import_str = 'from forms.models import Paciente, UnidadeSaude,Ficha, Formulario, Grupo, Grupo_Formulario'
    exec import_str
    form = Formulario.objects.get(id=formId)
    if not u'Implementação' in form.nome:
        return HttpResponseNotFound( form.nome )
        return HttpResponseNotFound(u'Permissão Negada')
    try:
        registers = retrieveFichas(int(patientId), form.tipo)
    except customError, e:
        msg = e.value
        if request.method == 'GET':
            url = settings.SITE_ROOT
            return render_to_response('error.html',
                locals(), RequestContext(request, {}))
        return HttpResponseNotFound('A busca não retornou resultados')
    patient = Paciente.objects.get(id=int(patientId))
    #Check groups rights
    groups       = Grupo.objects.filter(membros=request.user)
    us_list =  getListOfUS(request.user)
    gf = Grupo_Formulario.objects.filter(grupo__in = groups).filter(formulario= form)
    if not len(gf):
        return HttpResponseNotFound('A busca não retornou resultados')
    # Ugly fix. TODO check if this is valid for all situations.
    gf = gf[0]
    url = settings.SITE_ROOT
    return render_to_response('traffic_light_template.html',
        locals(), RequestContext(request, {}))

def ffrequired(request):
    return render_to_response('firefox.html',
        locals(), RequestContext(request, {}))

def retrieveFormName(request, formId):
	formulario = Formulario.objects.get(id=formId)
	return HttpResponse(formulario.nome)
