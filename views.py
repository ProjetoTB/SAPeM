#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os,sys
import tempfile2 as tempfile
import codecs
import tarfile
import cStringIO
import Image,ImageDraw

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

import settings
from forms.models import UnidadeSaude, Formulario, Ficha
from forms.HumanRegister import HumanRegister

import unicodedata

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
		return int(i)
	return i

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

def getOrderedFields(form):
	xmlDOM= getFieldsXML(form)
	elements = xmlDOM.getElementsByTagName('fields')[0].childNodes
	content = SortedDict(
		[(el.nodeName, getText(el.childNodes)) for el in elements
		if el.nodeType == el.ELEMENT_NODE]
	)
	return content




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


def homepage_view(request):
	import_str = "from forms.models import tipoFormulario, Formulario, Grupo, Grupo_Formulario, UserProfile"
	exec import_str
	if request.user.is_authenticated():
		us_favorite = None
		groups = Grupo.objects.filter(membros=request.user)
		try:
			us_favorite = request.user.get_profile().unidadesaude_favorita
			if not us_favorite: #User did not belong to a group
				# Check whether now he belongs to one and set a favorite US
				groups = Grupo.objects.filter(membros=request.user)
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
		registers = retrieveFichas(int(patientId))
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




def retrieveHumanRegister(patientId, form_type):
	return [HumanRegister(r, getOrderedFields(r.formulario))
			for r in retrieveFichas(int(patientId), form_type)]

def showPatientRegisters(request,patientId, formId):
	if not request.user.is_authenticated():
		return HttpResponseRedirect(settings.SITE_ROOT)
	import_str = 'from forms.models import Paciente, UnidadeSaude,Ficha, Formulario, Grupo, Grupo_Formulario'
	exec import_str
	form = Formulario.objects.get(id=formId)
	try:
		registers = retrieveHumanRegister(int(patientId), form.tipo)
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

def db2file(request, format='excel'):
	from forms.models import Ficha, Formulario
	response = HttpResponseNotFound('Formato invalido')
	if format == 'excel':
		import xlwt
		# Create file-like object
		response = HttpResponse(mimetype='application/ms-excel')
		filename = 'pacientes.xls'
		response['Content-Disposition'] = 'attachment; filename="'+ filename +'"'
		# Get Fichas grouped by Formularios
		forms = Formulario.objects.all()
		fichas = Ficha.objects.all()
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
			ws.col(0).width = 9000
			ws.col(1).width = 5000
			ws.col(2).width = 9000
			ws.col(3).width = 12000
			headers = {}
			index = 4
			for row, ficha in enumerate(fichas.filter(formulario=f)):
				ws.write(row+1,0,ficha.paciente.nome, body_style)
				ws.write(row+1,1,ficha.paciente.data_nascimento, body_style)
				ws.write(row+1,2, ficha.paciente.nome_mae, body_style)
				ws.write(row+1,3,ficha.unidadesaude.nome, body_style)
				# Parse ficha
				xml = parseString(ficha.conteudo.encode("utf-8" ))
				for field in xml.firstChild.childNodes:
					if not field.tagName in headers.keys():
						headers[field.tagName] = index
						ws.col(index).width = 4000
						ws.write(0, index, field.tagName ,header_style)
						index = index + 1
					try:
						ws.write(
						row+1,headers[field.tagName],
						', '.join(["%s"%(smart_int(f.firstChild.nodeValue))
							for f in xml.getElementsByTagName(field.tagName)]),
						body_style)
					except:
						pass
		wb.save(response)
	return response

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


	return HttpResponse(r)

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

def showFilters(request):
	############ TRIAGEM BASELINE HOSPITAL
	# TOSSE
	triagemBaselineHospital_tosseSim = 0
	triagemBaselineHospital_tosseNao = 0
	triagemBaselineHospital_tosseIgn = 0

	fichas = Ficha.objects.all().filter(formulario=1)

	for ficha in fichas:
		xmlContent = ficha.conteudo

		doc = parseString(xmlContent.encode('utf-8'))

		nodes = doc.firstChild.childNodes

		#Translate input tags
		fields = (
			'tosse',
			'hemoptoico',
			'sudorese',
			'febre',
			'emagrecimento',
			'dispneia',
			'fumante',
			'internacaoHospitalar'
		)

		for node in nodes:
			if node.firstChild and node.nodeName == "tosse":
				if node.firstChild.nodeValue == "sim":
					triagemBaselineHospital_tosseSim += 1
				elif node.firstChild.nodeValue == 'nao':
					triagemBaselineHospital_tosseNao += 1
				else:
					triagemBaselineHospital_tosseIgn += 1

	triagemBaselineHospital_tosseTotal = triagemBaselineHospital_tosseSim + triagemBaselineHospital_tosseNao + triagemBaselineHospital_tosseIgn

	# HEMOPTOICO
	triagemBaselineHospital_hemoptoicoSim = 0
	triagemBaselineHospital_hemoptoicoNao = 0
	triagemBaselineHospital_hemoptoicoIgn = 0

	fichas = Ficha.objects.all().filter(formulario=1)

	for ficha in fichas:
		xmlContent = ficha.conteudo

		doc = parseString(xmlContent.encode('utf-8'))

		nodes = doc.firstChild.childNodes

		for node in nodes:
			if node.firstChild and node.nodeName == "hemoptoico":
				if node.firstChild.nodeValue == "sim":
					triagemBaselineHospital_hemoptoicoSim += 1
				elif node.firstChild.nodeValue == 'nao':
					triagemBaselineHospital_hemoptoicoNao += 1
				else:
					triagemBaselineHospital_hemoptoicoIgn += 1

	triagemBaselineHospital_hemoptoicoTotal = triagemBaselineHospital_hemoptoicoSim + triagemBaselineHospital_hemoptoicoNao + triagemBaselineHospital_hemoptoicoIgn

	# SUDORESE
	triagemBaselineHospital_sudoreseSim = 0
	triagemBaselineHospital_sudoreseNao = 0
	triagemBaselineHospital_sudoreseIgn = 0

	fichas = Ficha.objects.all().filter(formulario=1)

	for ficha in fichas:
		xmlContent = ficha.conteudo

		doc = parseString(xmlContent.encode('utf-8'))

		nodes = doc.firstChild.childNodes

		for node in nodes:
			if node.firstChild and node.nodeName == "sudorese":
				if node.firstChild.nodeValue == "sim":
					triagemBaselineHospital_sudoreseSim += 1
				elif node.firstChild.nodeValue == 'nao':
					triagemBaselineHospital_sudoreseNao += 1
				else:
					triagemBaselineHospital_sudoreseIgn += 1

	triagemBaselineHospital_sudoreseTotal = triagemBaselineHospital_sudoreseSim + triagemBaselineHospital_sudoreseNao + triagemBaselineHospital_sudoreseIgn

	# FEBRE
	triagemBaselineHospital_febreSim = 0
	triagemBaselineHospital_febreNao = 0
	triagemBaselineHospital_febreIgn = 0

	fichas = Ficha.objects.all().filter(formulario=1)

	for ficha in fichas:
		xmlContent = ficha.conteudo

		doc = parseString(xmlContent.encode('utf-8'))

		nodes = doc.firstChild.childNodes

		for node in nodes:
			if node.firstChild and node.nodeName == "febre":
				if node.firstChild.nodeValue == "sim":
					triagemBaselineHospital_febreSim += 1
				elif node.firstChild.nodeValue == 'nao':
					triagemBaselineHospital_febreNao += 1
				else:
					triagemBaselineHospital_sudoreseIgn += 1

	triagemBaselineHospital_febreTotal = triagemBaselineHospital_febreSim + triagemBaselineHospital_febreNao + triagemBaselineHospital_febreIgn
	####################################
	############ TRIAGEM BASELINE AMBULATORIO
	# TOSSE
	triagemBaselineAmbulatorio_tosseSim = 0
	triagemBaselineAmbulatorio_tosseNao = 0
	triagemBaselineAmbulatorio_tosseIgn = 0

	fichas = Ficha.objects.all().filter(formulario=2)

	for ficha in fichas:
		xmlContent = ficha.conteudo

		doc = parseString(xmlContent.encode('utf-8'))

		nodes = doc.firstChild.childNodes

		for node in nodes:
			if node.firstChild and node.nodeName == "tosse":
				if node.firstChild.nodeValue == "sim":
					triagemBaselineAmbulatorio_tosseSim += 1
				elif node.firstChild.nodeValue == 'nao':
					triagemBaselineAmbulatorio_tosseNao += 1
				else:
					triagemBaselineAmbulatorio_tosseIgn += 1

	triagemBaselineAmbulatorio_tosseTotal = triagemBaselineAmbulatorio_tosseSim + triagemBaselineAmbulatorio_tosseNao + triagemBaselineAmbulatorio_tosseIgn

	# HEMOPTOICO
	triagemBaselineAmbulatorio_hemoptoicoSim = 0
	triagemBaselineAmbulatorio_hemoptoicoNao = 0
	triagemBaselineAmbulatorio_hemoptoicoIgn = 0

	fichas = Ficha.objects.all().filter(formulario=2)

	for ficha in fichas:
		xmlContent = ficha.conteudo

		doc = parseString(xmlContent.encode('utf-8'))

		nodes = doc.firstChild.childNodes

		for node in nodes:
			if node.firstChild and node.nodeName == "hemoptoico":
				if node.firstChild.nodeValue == "sim":
					triagemBaselineAmbulatorio_hemoptoicoSim += 1
				elif node.firstChild.nodeValue == 'nao':
					triagemBaselineAmbulatorio_hemoptoicoNao += 1
				else:
					triagemBaselineAmbulatorio_hemoptoicoIgn += 1

	triagemBaselineAmbulatorio_hemoptoicoTotal = triagemBaselineAmbulatorio_hemoptoicoSim + triagemBaselineAmbulatorio_hemoptoicoNao + triagemBaselineAmbulatorio_hemoptoicoIgn

	# SUDORESE
	triagemBaselineAmbulatorio_sudoreseSim = 0
	triagemBaselineAmbulatorio_sudoreseNao = 0
	triagemBaselineAmbulatorio_sudoreseIgn = 0

	fichas = Ficha.objects.all().filter(formulario=2)

	for ficha in fichas:
		xmlContent = ficha.conteudo

		doc = parseString(xmlContent.encode('utf-8'))

		nodes = doc.firstChild.childNodes

		for node in nodes:
			if node.firstChild and node.nodeName == "sudorese":
				if node.firstChild.nodeValue == "sim":
					triagemBaselineAmbulatorio_sudoreseSim += 1
				elif node.firstChild.nodeValue == 'nao':
					triagemBaselineAmbulatorio_sudoreseNao += 1
				else:
					triagemBaselineAmbulatorio_sudoreseIgn += 1

	triagemBaselineAmbulatorio_sudoreseTotal = triagemBaselineAmbulatorio_sudoreseSim + triagemBaselineAmbulatorio_sudoreseNao + triagemBaselineAmbulatorio_sudoreseIgn

	# FEBRE
	triagemBaselineAmbulatorio_febreSim = 0
	triagemBaselineAmbulatorio_febreNao = 0
	triagemBaselineAmbulatorio_febreIgn = 0

	fichas = Ficha.objects.all().filter(formulario=2)

	for ficha in fichas:
		xmlContent = ficha.conteudo

		doc = parseString(xmlContent.encode('utf-8'))

		nodes = doc.firstChild.childNodes

		for node in nodes:
			if node.firstChild and node.nodeName == "febre":
				if node.firstChild.nodeValue == "sim":
					triagemBaselineAmbulatorio_febreSim += 1
				elif node.firstChild.nodeValue == 'nao':
					triagemBaselineAmbulatorio_febreNao += 1
				else:
					triagemBaselineAmbulatorio_febreIgn += 1

	triagemBaselineAmbulatorio_febreTotal = triagemBaselineAmbulatorio_febreSim + triagemBaselineAmbulatorio_febreNao + triagemBaselineAmbulatorio_febreIgn
	####################################
	############ TRIAGEM IMPLEMENTACAO HOSPITAL
	# TOSSE
	triagemImplementacaoHospital_tosseSim = 0
	triagemImplementacaoHospital_tosseNao = 0
	triagemImplementacaoHospital_tosseIgn = 0

	fichas = Ficha.objects.all().filter(formulario=7)

	for ficha in fichas:
		xmlContent = ficha.conteudo

		doc = parseString(xmlContent.encode('utf-8'))

		nodes = doc.firstChild.childNodes

		for node in nodes:
			if node.firstChild and node.nodeName == "tosse":
				if node.firstChild.nodeValue == "sim":
					triagemImplementacaoHospital_tosseSim += 1
				elif node.firstChild.nodeValue == 'nao':
					triagemImplementacaoHospital_tosseNao += 1
				else:
					triagemImplementacaoHospital_tosseIgn += 1

	triagemImplementacaoHospital_tosseTotal = triagemImplementacaoHospital_tosseSim + triagemImplementacaoHospital_tosseNao + triagemImplementacaoHospital_tosseIgn

	# HEMOPTOICO
	triagemImplementacaoHospital_hemoptoicoSim = 0
	triagemImplementacaoHospital_hemoptoicoNao = 0
	triagemImplementacaoHospital_hemoptoicoIgn = 0

	fichas = Ficha.objects.all().filter(formulario=7)

	for ficha in fichas:
		xmlContent = ficha.conteudo

		doc = parseString(xmlContent.encode('utf-8'))

		nodes = doc.firstChild.childNodes

		for node in nodes:
			if node.firstChild and node.nodeName == "hemoptoico":
				if node.firstChild.nodeValue == "sim":
					triagemImplementacaoHospital_hemoptoicoSim += 1
				elif node.firstChild.nodeValue == 'nao':
					triagemImplementacaoHospital_hemoptoicoNao += 1
				else:
					triagemImplementacaoHospital_hemoptoicoIgn += 1

	triagemImplementacaoHospital_hemoptoicoTotal = triagemImplementacaoHospital_hemoptoicoSim + triagemImplementacaoHospital_hemoptoicoIgn + triagemImplementacaoHospital_hemoptoicoIgn

	# SUDORESE
	triagemImplementacaoHospital_sudoreseSim = 0
	triagemImplementacaoHospital_sudoreseNao = 0
	triagemImplementacaoHospital_sudoreseIgn = 0

	fichas = Ficha.objects.all().filter(formulario=7)

	for ficha in fichas:
		xmlContent = ficha.conteudo

		doc = parseString(xmlContent.encode('utf-8'))

		nodes = doc.firstChild.childNodes

		for node in nodes:
			if node.firstChild and node.nodeName == "sudorese":
				if node.firstChild.nodeValue == "sim":
					triagemImplementacaoHospital_sudoreseSim += 1
				elif node.firstChild.nodeValue == 'nao':
					triagemImplementacaoHospital_sudoreseNao += 1
				else:
					triagemImplementacaoHospital_sudoreseIgn += 1

	triagemImplementacaoHospital_sudoreseTotal = triagemImplementacaoHospital_sudoreseSim + triagemImplementacaoHospital_sudoreseNao + triagemImplementacaoHospital_sudoreseIgn

	# FEBRE
	triagemImplementacaoHospital_febreSim = 0
	triagemImplementacaoHospital_febreNao = 0
	triagemImplementacaoHospital_febreIgn = 0

	fichas = Ficha.objects.all().filter(formulario=7)

	for ficha in fichas:
		xmlContent = ficha.conteudo

		doc = parseString(xmlContent.encode('utf-8'))

		nodes = doc.firstChild.childNodes

		for node in nodes:
			if node.firstChild and node.nodeName == "febre":
				if node.firstChild.nodeValue == "sim":
					triagemImplementacaoHospital_febreSim += 1
				elif node.firstChild.nodeValue == 'nao':
					triagemImplementacaoHospital_febreNao += 1
				else:
					triagemImplementacaoHospital_febreIgn += 1

	triagemImplementacaoHospital_febreTotal = triagemImplementacaoHospital_febreSim + triagemImplementacaoHospital_febreNao + triagemImplementacaoHospital_febreIgn
	####################################
	############ TRIAGEM IMPLEMENTACAO AMBULATORIO
	# TOSSE
	triagemImplementacaoAmbulatorio_tosseSim = 0
	triagemImplementacaoAmbulatorio_tosseNao = 0
	triagemImplementacaoAmbulatorio_tosseIgn = 0

	fichas = Ficha.objects.all().filter(formulario=6)

	for ficha in fichas:
		xmlContent = ficha.conteudo

		doc = parseString(xmlContent.encode('utf-8'))

		nodes = doc.firstChild.childNodes

		for node in nodes:
			if node.firstChild and node.nodeName == "tosse":
				if node.firstChild.nodeValue == "sim":
					triagemImplementacaoAmbulatorio_tosseSim += 1
				elif node.firstChild.nodeValue == 'nao':
					triagemImplementacaoAmbulatorio_tosseNao += 1
				else:
					triagemImplementacaoAmbulatorio_tosseIgn += 1

	triagemImplementacaoAmbulatorio_tosseTotal = triagemImplementacaoAmbulatorio_tosseSim + triagemImplementacaoAmbulatorio_tosseNao + triagemImplementacaoAmbulatorio_tosseIgn

	# HEMOPTOICO
	triagemImplementacaoAmbulatorio_hemoptoicoSim = 0
	triagemImplementacaoAmbulatorio_hemoptoicoNao = 0
	triagemImplementacaoAmbulatorio_hemoptoicoIgn = 0

	fichas = Ficha.objects.all().filter(formulario=6)

	for ficha in fichas:
		xmlContent = ficha.conteudo

		doc = parseString(xmlContent.encode('utf-8'))

		nodes = doc.firstChild.childNodes

		for node in nodes:
			if node.firstChild and node.nodeName == "hemoptoico":
				if node.firstChild.nodeValue == "sim":
					triagemImplementacaoAmbulatorio_hemoptoicoSim += 1
				elif node.firstChild.nodeValue == 'nao':
					triagemImplementacaoAmbulatorio_hemoptoicoNao += 1
				else:
					triagemImplementacaoAmbulatorio_hemoptoicoIgn += 1

	triagemImplementacaoAmbulatorio_hemoptoicoTotal = triagemImplementacaoAmbulatorio_hemoptoicoSim + triagemImplementacaoAmbulatorio_hemoptoicoNao + triagemImplementacaoAmbulatorio_hemoptoicoIgn

	# SUDORESE
	triagemImplementacaoAmbulatorio_sudoreseSim = 0
	triagemImplementacaoAmbulatorio_sudoreseNao = 0
	triagemImplementacaoAmbulatorio_sudoreseIgn = 0

	fichas = Ficha.objects.all().filter(formulario=6)

	for ficha in fichas:
		xmlContent = ficha.conteudo

		doc = parseString(xmlContent.encode('utf-8'))

		nodes = doc.firstChild.childNodes

		for node in nodes:
			if node.firstChild and node.nodeName == "sudorese":
				if node.firstChild.nodeValue == "sim":
					triagemImplementacaoAmbulatorio_sudoreseSim += 1
				elif node.firstChild.nodeValue == 'nao':
					triagemImplementacaoAmbulatorio_sudoreseNao += 1
				else:
					triagemImplementacaoAmbulatorio_sudoreseIgn += 1

	triagemImplementacaoAmbulatorio_sudoreseTotal = triagemImplementacaoAmbulatorio_sudoreseSim + triagemImplementacaoAmbulatorio_sudoreseNao + triagemImplementacaoAmbulatorio_sudoreseIgn

	# FEBRE
	triagemImplementacaoAmbulatorio_febreSim = 0
	triagemImplementacaoAmbulatorio_febreNao = 0
	triagemImplementacaoAmbulatorio_febreIgn = 0

	fichas = Ficha.objects.all().filter(formulario=6)

	for ficha in fichas:
		xmlContent = ficha.conteudo

		doc = parseString(xmlContent.encode('utf-8'))

		nodes = doc.firstChild.childNodes

		for node in nodes:
			if node.firstChild and node.nodeName == "febre":
				if node.firstChild.nodeValue == "sim":
					triagemImplementacaoAmbulatorio_febreSim += 1
				elif node.firstChild.nodeValue == 'nao':
					triagemImplementacaoAmbulatorio_febreNao += 1
				else:
					triagemImplementacaoAmbulatorio_febreIgn += 1

	triagemImplementacaoAmbulatorio_febreTotal = triagemImplementacaoAmbulatorio_febreSim + triagemImplementacaoAmbulatorio_febreNao + triagemImplementacaoAmbulatorio_febreIgn

	return render_to_response('filters.html', locals(), RequestContext(request, {}))
