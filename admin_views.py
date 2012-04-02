#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys
# Work around made due the fact production version has an outdated version of
# tempfile module
import tempfile2 as tempfile
import tarfile
from datetime import datetime, timedelta
import time

from django import forms
from django.contrib.admin.util import model_ngettext
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.db.models import Count
from django.forms import ModelForm
from django.http import HttpResponse,HttpResponseNotFound, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils import simplejson
from django.utils.datastructures import SortedDict
from django.utils.translation import ugettext_lazy, ugettext as _

from forms.models import Formulario, tipoFormulario, UnidadeSaude, Ficha

import settings


class FormularioForm(forms.Form):
	tipo         = forms.ChoiceField()
	arquivo      = forms.FileField(max_length=300)
	descricao    = forms.CharField(widget=forms.Textarea())
	permitir_insercao_multipla    = forms.BooleanField (required=False)
	def __init__(self, *args, **kwargs):
		super(FormularioForm,self).__init__(*args,**kwargs)
		self.fields['tipo'].choices = self.get_type_options()
		self.fields['permitir_insercao_multipla'].verbose_name = u"Permitir a inserção de múltiplas entradas desse formulário"
	def get_type_options(self):
		import_forms = 'from forms.models import *'
		exec import_forms
		tp_list = tipoFormulario.objects.all()
		types = [[type.nome, type.nome] for type in tp_list]
		types.reverse()
		types.append(['', '--------'])
		types.reverse()
		return types

class FormularioEditForm(ModelForm):
	class Meta:
		model = Formulario
		exclude = ('nome', 'version','path', 'data_insercao')

class UploadError(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return self.value

def handle_uploaded_file(f):
	destination = tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False)
	for chunk in f.chunks():
		destination.write(chunk)
	destination.seek(0)
	destination.close()
	tar = tarfile.open(destination.name)
	final_path = "%s/%s"%( os.path.join(os.path.dirname(os.path.realpath(__file__)), 'modules'), '.'.join(f.name.split('.')[0:-2]))
	dirname, filename = os.path.split(final_path)
	prefix, suffix = os.path.splitext(filename)
	final_path = tempfile.mkdtemp(suffix, prefix+'_', dirname)
	tar.extractall(path=final_path)
	tar.close()
	os.remove(destination.name)
	return final_path

class meta_data:
	def __init__(self, v, v_plural=None):
		self.verbose_name = v
		if not v_plural:
			v_plural = v + 's'
		self.verbose_name_plural = v_plural

def add_formulario(request, app_label='Forms' ):
	if not request.user.is_authenticated():
		return HttpResponseRedirect('/admin/')
	opts = meta_data(u'Formulário')
	if request.method == 'POST':
		form = FormularioForm(request.POST, request.FILES)
		if form.is_valid():
			path = handle_uploaded_file(request.FILES['arquivo'])
			pathname, moduleFormName = os.path.split(path)
			pathname ='%s/'%(pathname,)
			if not pathname in sys.path:
				sys.path.append(pathname)
			moduleForm = __import__(moduleFormName)
			#try:
			#	moduleForm = __import__(moduleFormName)
			#except ImportError:
			#	return HttpResponseRedirect(settings.SITE_ROOT + '/admin/forms/formulario/')
			tipoForm = tipoFormulario.objects.get(nome=form.cleaned_data['tipo'])
			tp =form.cleaned_data['permitir_insercao_multipla']
			if tp:
				tp = True
			else:
				tp = False
			newForm = Formulario(
				nome=moduleForm.name,
				version=moduleForm.version,
				path=path,
				tipo_id=tipoForm.id,
				descricao=form.cleaned_data['descricao'],
				permitir_insercao_multipla = tp
			)
			newForm.save()
			return HttpResponseRedirect(settings.SITE_ROOT + 'admin/forms/formulario/')
	else:
		form = FormularioForm(auto_id=True)
	add = True
	return render_to_response('change_form.html',
			locals(), RequestContext(request, {}))

def edit_formulario(request, f_id, app_label='Forms'):
	if not request.user.is_authenticated():
		return HttpResponseRedirect(settings.SITE_ROOT + 'admin/')
	f = Formulario.objects.get(id=int(f_id))
	if request.method == 'POST':
		form = FormularioEditForm(request.POST, instance=f)
		if form.is_valid():
			tipoForm = tipoFormulario.objects.filter(nome=form.cleaned_data['tipo'])
			f.tipo = tipoForm[0]
			f.descricao = form.cleaned_data['descricao']
			f.save()
			return HttpResponseRedirect(settings.SITE_ROOT +'admin/forms/formulario/')
	else:
		form = FormularioEditForm(instance=f)
	opts = meta_data(u'Formulário')
	original = form.Meta().model().__str__()
	return render_to_response('change_form.html',
			locals(), RequestContext(request, {}))

def getMonthList(now, stDate, endDate):
	dateRange =[now - timedelta(days=stDate), now-timedelta(days=endDate)]
	dt1, dt2 = dateRange
	start_month=dt1.month
	end_months=(dt2.year-dt1.year)*12 + dt2.month+1
	return [datetime(year=yr, month=mn, day=1) for (yr, mn) in (
          ((m - 1) / 12 + dt1.year, (m - 1) % 12 + 1) for m in range(start_month, end_months)
    )]


def log_unidadesaude(request, stDate=365, endDate=0):
	if not request.user.is_authenticated():
		return HttpResponseRedirect(settings.SITE_ROOT + 'admin/')
	"""
	Summary report
	"""
	now= datetime.now()
	truncate_date = connection.ops.date_trunc_sql('month', 'data_insercao')
	fichas_report = Ficha.objects.filter(
                                            data_insercao__gte=now -timedelta(days=stDate),
                                            data_insercao__lte=now -timedelta(days=endDate)
                                        ).\
                            extra(select={'month': truncate_date}).\
                            values('unidadesaude__id', 'unidadesaude__nome', 'month').\
                            annotate(numero_fichas=Count('pk')).\
                            order_by('-month')
	fichas_report = [ dict([
         ('unidadesaude__nome', l['unidadesaude__nome']),
         ('unidadesaude__id', l['unidadesaude__id']),
         ('month', datetime.strptime(l['month'].split(' ')[0], '%Y-%m-%d')),
         ('numero_fichas', l['numero_fichas'])
     ]) for l in fichas_report]
	columns = getMonthList(now, stDate, endDate)
	rows = UnidadeSaude.objects.values('nome', 'id').order_by('nome')
	return render_to_response('admin/unidadesaude_log.html',
			locals(), RequestContext(request, {}))

def log_unidadesaude_by_form(request, healthUnit,stDate=365, endDate=0):
	if not request.user.is_authenticated():
		return HttpResponseRedirect(settings.SITE_ROOT + 'admin/')
	now= datetime.now()
	try:
		us = UnidadeSaude.objects.get(pk=int(healthUnit))
	except:
		return HttpResponseNotFound('Id de unidade errado')
	truncate_date = connection.ops.date_trunc_sql('month', 'forms_ficha.data_insercao')
	fichas_report = Ficha.objects.\
                                   filter(
                                            unidadesaude=us,
                                            data_insercao__gte=now -timedelta(days=stDate),
                                            data_insercao__lte=now -timedelta(days=endDate)
                                        ).\
                            extra(select={'month': truncate_date}).\
                            values('formulario__nome', 'month').\
                            annotate(numero_fichas=Count('pk')).\
                            order_by('-month')
	fichas_report = [ dict([
         ('formulario__nome', l['formulario__nome']),
         ('month', datetime.strptime(l['month'].split(' ')[0], '%Y-%m-%d').strftime('%Y%m')),
         ('numero_fichas', l['numero_fichas'])
     ]) for l in fichas_report]
	columns = [dt.strftime('%Y%m') for dt in getMonthList(now, stDate, endDate)]
	forms = Formulario.objects.all()
	rows = [r.nome for r in forms]
	table_data = SortedDict().fromkeys(rows)
	for k in table_data.keys():
		table_data[k] = SortedDict().fromkeys(columns, 0)
	for f in fichas_report:
		table_data[f['formulario__nome']][f['month']] = f['numero_fichas']
	return json_response(table_data)

def json_response(data):
	return HttpResponse(
		simplejson.dumps(data),
		content_type = 'application/javascript; charset=utf8'
	)

add_formulario = staff_member_required(add_formulario)
edit_formulario = staff_member_required(edit_formulario)
log_unidadesaude = staff_member_required(log_unidadesaude)
log_unidadesaude_by_form = staff_member_required(log_unidadesaude_by_form)
