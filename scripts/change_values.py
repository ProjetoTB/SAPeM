from forms.models import Ficha, Paciente
from xml.dom.minidom import parseString, getDOMImplementation
impl = getDOMImplementation()

tag = 'diagnostico'

fichas = Ficha.objects.filter(formulario__tipo__nome='Consulta')

wrong_registers = []


fix = { 
	"melhora"    : "tb_pulmonar",
	"inalterado" : "tb_extra-pulmonar",
	"piorado"    : "tb_pulmonar-extra",
	"nao_tb"     : "nao_tb",
	"ignorado"   : "ignorado"
}

for f in fichas:
	xml = parseString(f.conteudo.encode('utf-8'))
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
		if el.tagName == tag:
			new_tag = new_xml.createElement(tag)
			nodeValue = new_xml.createTextNode(fix[el.childNodes[0].nodeValue])
			new_tag.appendChild(nodeValue)
			root_tag.appendChild(new_tag)
		else:
			root_tag.appendChild(el.cloneNode(True))
	f.conteudo = new_xml.toxml()
	f.save()
	del new_xml, xml
