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

import settings
from forms.models import Formulario
from forms.models import UnidadeSaude
from reports.models import Configuracao

from xml.dom.minidom import parseString, getDOMImplementation

def smart_truncate_string(str, size):
	if len(str) < size:
		return str
	return str[:size-3].rsplit(' ', 1)[0] + ' ...'

def smart_int(i):
	if i.isdigit():
		return int(i)
	return i

def create_configuration_reports(request):
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
		return HttpResponseRedirect('%s/reports/view/'%url)
	forms_list = Formulario.objects.all()
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

def get_questions(request, formId):
	forms = Formulario.objects.get(id=formId)
	file = open("%s/questions.xml"%(forms.path), 'r')
	content = file.read()
	file.close()

	return HttpResponse(content, mimetype='text/xml');

def getText(nodelist):
	rc = []
	for node in nodelist:
		if node.nodeType == node.TEXT_NODE:
			rc.append(node.data)
	return ''.join(rc)

def configuration_db2file(request, sid,format='excel'):
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
		forms = Formulario.objects.all()
		fichas = Ficha.objects.all()
	response = HttpResponseNotFound('Formato invalido')
	if format == 'excel':
		import xlwt
		# Create file-like object
		response = HttpResponse(mimetype='application/ms-excel')
		filename = 'pacientes.xls'
		response['Content-Disposition'] = 'attachment; filename="'+ filename +'"'
		# Get Fichas grouped by Formularios
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
