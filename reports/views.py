#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Author:		Andressa Sivolella <andressasivolella@gmail.com>
# Date:			2011-12-04

import os, sys
from datetime import datetime, date, time

from django.http import HttpResponse,HttpResponseNotFound, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.db import IntegrityError
from django.contrib.messages import constants as messages
from django.utils.datastructures import SortedDict

import settings
from reports.models import Configuracao

from xml.dom.minidom import parse, parseString, getDOMImplementation

def smart_truncate_string(str, size):
	if len(str) < size:
		return str
	return str[:size-3].rsplit(' ', 1)[0] + ' ...'

def smart_int(i):
	if i.isdigit():
		return int(i)
	return i

def create_configuration_reports(request):
	from forms.models import Formulario, UnidadeSaude
	url = settings.SITE_ROOT
	if request.method == "POST":
		form = request.POST
		xmlStr = u'<?xml version="1.0" encoding="utf-8"?>'
		xmlStr += u'<settings>'
		xmlStr += '<formularios>'
		for formId in form.getlist('formularios'):
			xmlStr += '<id>%s</id>'%formId
		xmlStr += '</formularios>'
		xmlStr += '<unidadeSaude>'
		for usId in form.getlist('unidadeSaude'):
			xmlStr += '<id>%s</id>'%usId
		xmlStr += '</unidadeSaude>'
		xmlStr += u'</settings>'
		try:
			reportSettings = Configuracao()
			reportSettings.name = form["name"]
			reportSettings.user = request.user
			reportSettings.settings = xmlStr
			reportSettings.save()
			#messages.success(request, 'Configuração salva')
		except IntegrityError, e:
			pass
			#messages.add_message(request, messages.INFO, 'Hello world.')
			#messages.info(request, 'Three credits remain in your account.')
		return HttpResponseRedirect('%sreports/view/'%url)
	# Permitindo criação de relatórios apenas para formulários de Triagem
	#forms_list = Formulario.objects.all()
	forms_list = Formulario.objects.order_by('nome')[3:]
	unidades = UnidadeSaude.objects.all()
	return render_to_response('configReport.html',
			locals(), RequestContext(request, {}))

def view_configuration_reports(reports, sId):
	url = settings.SITE_ROOT
	try:
		s = Configuracao.objects.get(pk=sId)
		s.delete()
	except Configuracao.DoesNotExist:
		pass
	return HttpResponseRedirect('%s/reports/view/'%url)

def view_configuration_reports(request):
	if request.method == "POST":
		msg = request.POST['msg']
	settings  = Configuracao.objects.all()
	return render_to_response('viewReports.html',
			locals(), RequestContext(request, {}))

def remove_configuration_reports(request, configId):
	url = settings.SITE_ROOT
	try:
		d = Configuracao.objects.get(pk=configId)
		d.delete()
	except Configuracao.DoesNotExist:
		pass
	return HttpResponseRedirect('%sreports/view'%url)

def getText(nodelist):
	rc = []
	for node in nodelist:
		if node.nodeType == node.TEXT_NODE:
			rc.append(node.data)
	return ''.join(rc)

def configuration_db2file(request, sid,format='csv'):
	from forms.models import Ficha, Formulario
	try:
		d = Configuracao.objects.get(pk=sid)
		xmlStr = d.settings
		dom = parseString(xmlStr)
		forms_node = dom.getElementsByTagName('formularios')[0]
		ids = []
		for idNode in forms_node.getElementsByTagName('id'):
			ids.append(int(getText(idNode.childNodes)))
		us = dom.getElementsByTagName('unidadeSaude')[0]
		ids_us = []
		for idNode in us.getElementsByTagName('id'):
			ids_us.append(int(getText(idNode.childNodes)))
		forms = Formulario.objects.filter(pk__in=ids)
		fichas = Ficha.objects.filter(unidadesaude__id__in=ids_us, formulario__in=forms)
	except Configuracao.DoesNotExist:
		forms = Formulario.objects.filter(tipo__nome= 'Triagem')
		fichas = Ficha.objects.all()
	response = HttpResponseNotFound('Formato invalido')
	if format == 'csv':
		import csv, random
		import string
		valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
		#Generate a file for each Triagem and complete with the other forms
		fields = []
		files = []
		triagens = forms
		other_forms_fields = SortedDict()
		for f_type in ['Consulta', 'Exames', 'Follow-up']:
			other_forms = Formulario.objects.filter(tipo__nome=f_type)
			for f in other_forms:
				other_forms_fields[f.id] = getOrderedFields(f, show_form=True)
		for tForm in triagens:
			form_fields = SortedDict()
			form_fields[tForm.id] = getOrderedFields(tForm, show_form=True)
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
			#content
			fichas_triagem = Ficha.objects.filter(unidadesaude__id__in=ids_us, formulario=tForm)
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
							data[paciente][field.tagName] = ', '.join(["%s"%(smart_int(f.firstChild.nodeValue))
								for f in xml.getElementsByTagName(field.tagName)])
						except:
							pass
			for id, tags in data.iteritems():
				writer.writerow([tags[tag].encode('utf-8') for tag  in headerKeysList])
				#writer.writerow([k for k in tags.iterkeys()])
			csvfile.close()
		return zip_to_response(files, 'pacientes.zip')
	return HttpResponseNotFound("File format not found")

def show_report(request, configId):
	from tbForms.views import homepage_view, sapem_login
	if request.method == 'POST':
		return homepage_view(request)

	config = Configuracao.objects.get(id=configId)
	return render_to_response('reports.html',
			locals(), RequestContext(request, {}))

def get_configSettingsXml(request, configId):
	config = Configuracao.objects.get(id=configId)
	xmlStr = config.settings
	return HttpResponse( xmlStr, mimetype="application/xhtml+xml" )

def get_fichaValue(conteudo, tagname):
	xml = parseString(conteudo.encode('utf-8'))
	for f in xml.getElementsByTagName(tagname):
		return (f.childNodes[0].nodeValue)

def get_ageGroups():
	return [range(0,26), range(26, 31), range(31, 41), range(41, 51), range(51, 120)]

def get_ageGroupsLabels():
	return ['0 - 25 anos', '26 - 30 anos', '31 - 40 anos', '41 - 50 anos', 'Acima de 50 anos']

def get_ageGroup(age):
	ages = get_ageGroups()
	for group in xrange(len(ages)):
		if age in ages[group]:
			return group

def get_dataXml(request, configId, formId, variable):
	from forms.models import Ficha
	json = ''


	fichas = Ficha.objects.filter(formulario__id=formId, unidadesaude__id__in=request.GET["us"].split(','))

	if fichas.count() > 0:
		if variable == 'idade':
			legend = get_ageGroupsLabels()
			result = []

			for a in legend:
				result.append(0)

			values = []
			for f in fichas:
				values.append(get_fichaValue(f.conteudo, variable))
		
			values.sort()
			for v in values:
				result[get_ageGroup(int(v))] += 1

		json = "{"
		for i in xrange(len(legend) - 1):
			json += "\"%s\" : %d, "%(legend[i], result[i])
		json += "\"%s\" : %d}"%(legend[len(legend) - 1], result[len(result) - 1])

	if json == '':
		response = HttpResponseNotFound('Nenhuma ficha foi encontrada!')
	else:
		response = HttpResponse( json )

	return response

def getOrderedFields(form, show_form=False, number_multifields=4):
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
								content["%s_%d"%(m_el.nodeName, idx)] = \
									"%s %s %d"%(getText(m_el.childNodes),
									fieldsetName, idx)
							else:
								content["%s_%d"%(m_el.nodeName, idx)] = \
									"%s %s %d"%(getText(m_el.childNodes),
									fieldsetName, idx)
			else:
				if el.nodeType == el.ELEMENT_NODE:
					if show_form:
						content[el.nodeName] = "%s - %s"%(form.tipo.nome, getText(el.childNodes))
					else:
						content[el.nodeName] = getText(el.childNodes)

		return content
	return {}

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

