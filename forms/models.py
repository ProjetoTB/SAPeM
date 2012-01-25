#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
from django.db import models
from django.contrib.auth.models import User, UserManager
from django.contrib.auth.models import Group

class UnidadeSaude(models.Model):
	nome            = models.CharField(max_length=300,   blank=False)
	CEP             = models.CharField(max_length=9,     blank=False)
	rua             = models.CharField(max_length=300,   blank=False)
	numero          = models.CharField(max_length=10,    blank=True, verbose_name=u'Número')
	complemento     = models.CharField(max_length=30,    blank=True)
	cidade          = models.CharField(max_length=300,   blank=False)
	UF              = models.CharField(max_length=2,     blank=False)
	relacionamento  = models.ManyToManyField("self", symmetrical=True, blank=True)
	def __str__(self):
		return self.nome.encode('utf-8')
	class Meta():
		verbose_name_plural = u'unidades de saúde'
		verbose_name        = u'unidade de saúde'

class Paciente(models.Model):
	nome            = models.CharField(max_length=300)
	nome_mae        = models.CharField(max_length=300)
	data_nascimento = models.CharField(max_length=10)
	class Meta:
		unique_together = ('nome', 'nome_mae', 'data_nascimento')

class tipoFormulario(models.Model):
	nome            = models.CharField(max_length=300)
	def __str__(self):
		return self.nome.encode('utf-8')
	class Meta():
		verbose_name_plural = u'tipos de formulário'

class Formulario(models.Model):
	nome            = models.CharField(max_length=300)
	version         = models.CharField(max_length=300)
	tipo            = models.ForeignKey(tipoFormulario)
	permitir_insercao_multipla = models.BooleanField(u"Permitir a inserção de múltiplas entradas desse formulário")
	path            = models.CharField(max_length=300)
	descricao       = models.TextField()
	data_insercao   = models.DateTimeField(auto_now_add=True)
	data_insercao.short_description = u'Data de Inserção do Formulário'
	def __str__(self):
		return self.nome.encode('utf-8')
	#Custom delete action
	def delete(self, *args, **kwargs):
		try:
			shutil.rmtree(self.path)
		except OSError:
			pass
		super(Formulario, self).delete(*args, **kwargs)
	class Meta:
		verbose_name_plural = u'formulários'
		verbose_name        = u'formulário'

class Ficha(models.Model):
	paciente                  = models.ForeignKey(Paciente)
	formulario                = models.ForeignKey(Formulario)
	unidadesaude              = models.ForeignKey(UnidadeSaude)
	conteudo                  = models.TextField()
	data_insercao             = models.DateTimeField(auto_now_add=True)
	data_ultima_modificacao   = models.DateTimeField(auto_now=True)
	class Meta:
		unique_together = ('paciente', 'formulario', 'unidadesaude', 'data_insercao')

class UserProfile(models.Model):
	unidadesaude_favorita = models.ForeignKey(UnidadeSaude, null=True)
	user = models.ForeignKey(User, unique=True)

class Grupo(models.Model):
	nome            = models.CharField(max_length=200)
	unidadesaude    = models.ForeignKey(UnidadeSaude)
	membros         = models.ManyToManyField(User, related_name='grupos', blank=True)
	def __str__(self):
		return self.nome.encode('utf-8')

class HistoricoFicha(models.Model):
	ficha                     = models.ForeignKey(Ficha)
	conteudo                  = models.TextField()
	data_ultima_modificacao   = models.DateTimeField(auto_now=True)

class Grupo_Formulario(models.Model):
	CHOICES = (('N', 'Nenhuma') , ('L', 'Leitura'), ('T', u'Leitura e Modificação'))
	grupo = models.ForeignKey(Grupo)
	formulario = models.ForeignKey(Formulario)
	permissao = models.CharField(max_length = 1, choices=CHOICES)
	permissao.short_description = u'permissão'

