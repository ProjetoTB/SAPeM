
from forms.models import Ficha, Paciente
from xml.dom.minidom import parseString, getDOMImplementation
impl = getDOMImplementation()


oldTag = 'fitaHain'
newTag = 'fitaHainRealizado'

fichas = Ficha.objects.filter(formulario__tipo__nome='Exames')

wrong_registers = []

for f in fichas:
	xml = parseString(f.conteudo.encode('utf-8'))
	try:
		if len(xml.getElementsByTagName(oldTag)[0].childNodes):
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
		if el.tagName == oldTag:
			new_tag = new_xml.createElement(newTag)
			for chn in el.childNodes:
				new_tag.appendChild(chn)
			root_tag.appendChild(new_tag)
		else:
			root_tag.appendChild(el.cloneNode(True))
	f.conteudo = new_xml.toxml()
	f.save()
	del new_xml, xml
