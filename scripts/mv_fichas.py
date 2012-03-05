from forms.models import Ficha, Paciente

import unicodedata

fichas   = Ficha.objects.filter(paciente__id=593)
paciente = Paciente.objects.get(id=731)

for f in fichas:
	conteudo                = f.conteudo
	data_insercao           = f.data_insercao
	data_ultima_modificacao = f.data_ultima_modificacao

	if f.formulario.id != 6: # se nao estiver tratando do Triagem Implementacao...
		new = Ficha(paciente=paciente, formulario=f.formulario, unidadesaude=f.unidadesaude, conteudo=conteudo, data_insercao=data_insercao, data_ultima_modificacao=data_ultima_modificacao)
		new.save()
	print 'Ficha ', f.formulario.nome, ' movida com sucesso'
