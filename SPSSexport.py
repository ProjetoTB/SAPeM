#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement

import datetime, time
import locale

from xml.dom.minidom import parse, parseString, getDOMImplementation

from django.core.management import setup_environ
import settings
setup_environ(settings)

from forms.models import *

from savReaderWriter import *

def getText(nodelist):
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)

def fichas2Dict(fichas):
    pacienteFichas = {}
    for ficha in fichas:
        try:
            pacienteFichas[ficha.formulario.id]
            return None
        except KeyError:
            conteudo = {}
            xml = parseString(ficha.conteudo.encode("utf-8"))
            for field in xml.firstChild.childNodes:
                for f in xml.getElementsByTagName(field.tagName):
                    try:
                        conteudo[field.tagName] = f.firstChild.nodeValue.encode("utf-8")
                    except AttributeError: pass
            try:
                conteudo["etapa"] = ficha.formulario.nome.split(" ")[1].encode("utf-8")
                conteudo["unidade"] = int(ficha.unidadesaude.id)
            except IndexError: pass #Formulario Exames ou FollowUp
            pacienteFichas[ficha.formulario.id] = conteudo
    return pacienteFichas

if __name__ == "__main__":
    locale.setlocale(locale.LC_TIME, "pt_BR.utf8")
    gregorianEpoch = datetime.datetime(1582, 10, 14, 0, 0, 0)

    mapping = os.path.join(os.path.dirname(__file__), "exportconfig/spssMapping.xml")

    file = open(os.path.join(os.path.dirname(__file__),"exportconfig/codifiedAnswers"), "rb")
    codifiedAnswers = eval(file.read())
    file.close()

    names     = []
    types     = {}
    format    = {}
    dom = parse(mapping)
    elements = dom.getElementsByTagName('spss')[0].childNodes
    header = []

    file = open(os.path.join(os.path.dirname(__file__), "exportconfig/values"), "rb")
    values = eval(file.read().decode("utf-8"))
    file.close()

    for el in elements:
        column = {}
        try:
            forms = el.getElementsByTagName("form")
            for f in forms:
                if f.nodeType == f.ELEMENT_NODE:
                    try:
                        column[int(f.attributes["id"].value)] = getText(f.childNodes)
                    except ValueError: pass
        except AttributeError: pass
        if el.nodeType == el.ELEMENT_NODE:
            names.append(el.nodeName.encode("utf-8"))
            types[el.nodeName.encode("utf-8")] = int(el.attributes['type'].value)
            format[el.nodeName.encode("utf-8")] = el.attributes['format'].value
            header.append(column)
    records = []

    fichas = Ficha.objects.filter(unidadesaude__id=13)

    pacientes = []

    for ficha in fichas:
        if ficha.paciente.id not in pacientes:
            pacientes.append(ficha.paciente.id)

    for id in pacientes:
        fichas = Ficha.objects.filter(paciente__id=id)
        register = []
        pacienteFichas = fichas2Dict(fichas)
        for column in header:
            answer = ""
            for form, question in column.items():
                try:
                    answer = codifiedAnswers[question][pacienteFichas[int(form)][question]]
                except:
                    try:
                        answer = int(pacienteFichas[int(form)][question])
                    except:
                        try:
                            answer = float(pacienteFichas[int(form)][question])
                        except:
                            try:
                                answer = (datetime.datetime.strptime(pacienteFichas[int(form)][question], "%d/%m/%Y") - gregorianEpoch).total_seconds()
                            except:
                                try:
                                    answer = (datetime.datetime.strptime(pacienteFichas[int(form)][question].split(", ")[1].lower(), "%d de %B de %Y") - gregorianEpoch).total_seconds()
                                except:
                                    try:
                                        answer = (datetime.datetime.strptime(pacienteFichas[int(form)][question].lower(), "%d de %B de %Y") - gregorianEpoch).total_seconds()
                                    except:
                                        try:
                                            answer = pacienteFichas[int(form)][question]
                                        except: pass
            register.append(answer)
        records.append(register)
    file = "%s/%s"%(sys.argv[1], sys.argv[2])

    try:
        with SavWriter(savFileName=file, varNames=names, varTypes=types, valueLabels=values, formats=format, ioUtf8=True, ioLocale="pt_BR.utf8") as sav:
            sav.writerows(records)
    except:
        try:
            userfile = Arquivo.objects.get(id=int(sys.argv[2].split(".sav")[0]))
            userfile.status = "E"
            userfile.save()
        except DoesNotExist:
            print "ERROR: there is not register on 'Arquivo' table with '%s' id"%(sys.argv[2].split(".sav")[0])
    try:
        userfile = Arquivo.objects.get(id=int(sys.argv[2].split(".sav")[0]))
        userfile.status = "D"
        userfile.data_geracao = datetime.datetime.now()
        userfile.save()
    except DoesNotExist:
        print "ERROR: there is not register on 'Arquivo' table with '%s' id"%(sys.argv[2].split(".sav")[0])

