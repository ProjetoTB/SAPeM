
from forms.models import Ficha, Paciente
from xml.dom.minidom import parseString, getDOMImplementation
impl = getDOMImplementation()

parentTag = 'exameSida'
tag = 'sida'

fichas = Ficha.objects.filter(formulario__tipo__nome='Exames')

wrong_registers = []

for f in fichas:
	xml = parseString(f.conteudo.encode('utf-8'))
	for chn_ptag in xml.getElementsByTagName(parentTag)[0].childNodes:
		if chn_ptag.nodeValue != 'sim':
			try:
				if len(xml.getElementsByTagName(tag)[0].childNodes):
					wrong_registers.append(f)
			except IndexError:
				pass

print 'Found ', len(wrong_registers), ' wrong registers'
for f in wrong_registers:
	print 'Fixing ficha:', f.id
	xml = parseString(f.conteudo.encode('utf-8'))
	new_xml = impl.createDocument(None, xml.firstChild.tagName, None)
	root_tag = new_xml.documentElement
	for el in xml.getElementsByTagName('documento')[0].childNodes:
		if el.tagName != tag:
			new_tag = new_xml.createElement(el.tagName)
			for chn in el.childNodes:
				new_tag.appendChild(chn)
			root_tag.appendChild(new_tag)
	f.conteudo = new_xml.toxml()
	f.save()
	del new_xml, xml
