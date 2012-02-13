from forms.models import Ficha, Paciente, UnidadeSaude

import unicodedata

def not_combining(char):
	return unicodedata.category(char) != 'Mn'

def strip_accents(text, encoding='utf-8'):
	unicode_text= unicodedata.normalize('NFD', text.decode(encoding))
	return filter(not_combining, unicode_text).encode(encoding)

file  = open('pacientes.txt', 'r')
output = open('log_pacientes_unidades', 'w')
us = UnidadeSaude.objects.get(id=5)
not_found = []
for pName in file:
	pName = pName.strip('\t\n\r')
	fichas = Ficha.objects.filter(paciente__nome__iexact=pName)
	if not len(fichas):
		pName = strip_accents(pName)
		fichas = Ficha.objects.filter(paciente__nome__iexact=pName)
	for f in fichas:
		if f.unidadesaude != us:
			output.write(f.paciente.nome)
			output.write('Movendo paciente de %s para %s\n'%(f.unidadesaude.nome,  us.nome))
			f.unidadesaude = us
			f.save()
	if len(fichas) == 0:
		not_found.append(pName)

output.write('NOT FOUND\n')
output.write(','.join(not_found))


fichas = Ficha.objects.filter(formulario__tipo__nome='Triagem', unidadesaude=us)
pacientes = [f.paciente for f in fichas]

output.write('Segunda Tentativa\n')
for p in pacientes:
	fichas = Ficha.objects.filter(paciente=p)
	for f in fichas:
		if f.unidadesaude != us:
			output.write('%s\n'%p.nome)
			output.write('Movendo paciente de %s para %s\n'%(f.unidadesaude.nome,  us.nome))
			f.unidadesaude = us
			f.save()

output.close()
