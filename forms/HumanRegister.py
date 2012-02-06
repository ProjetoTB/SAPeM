#!/usr/bin/env python
# -*- coding: utf-8 -*-

from xml.dom.minidom import parse, parseString, getDOMImplementation
from django.utils.datastructures import SortedDict

def getText(nodelist):
	rc = []
	for node in nodelist:
		if node.nodeType == node.TEXT_NODE:
			rc.append(node.data)
	return ''.join(rc)

class HumanRegister:
	def __init__(self, register, fields):
		self.id                = register.id
		self.paciente                = register.paciente
		self.formulario              = register.formulario
		self.unidadesaude            = register.unidadesaude
		self.data_insercao           = register.data_insercao
		self.data_ultima_modificacao = register.data_ultima_modificacao
		self.conteudo                = register.conteudo
		xml = parseString(register.conteudo.encode('utf-8'))
		answer = {
			u"sim": u"Sim ",
			u"nao": u"Não ",
			u"naoTB": u"Não possui TB "
		}
		#try:
		conteudo = SortedDict()
		for name, label in fields.iteritems():
			iFields = len(xml.getElementsByTagName(name))
			if iFields:
				for idx in range(iFields):
					a =  getText(xml.getElementsByTagName(name)[idx].childNodes)
					if len(a) != 0:
						try:
							dictTable = conteudo[name]
						except KeyError:
							conteudo[name]={"label": label, "value": answer.get(a, a)}
							continue
						conteudo[name]['value'] = ', '.join([answer.get(a,a), dictTable['value']])

		if len(conteudo) == 0:
			elements = xml.firstChild.childNodes
			conteudo = SortedDict()
			for el in elements:
				if el.nodeType == el.ELEMENT_NODE:
					a =  getText(el.childNodes)
					conteudo[el.nodeName] = {"label": el.nodeName,"value":answer.get(a, a)}
		self.conteudo = conteudo
