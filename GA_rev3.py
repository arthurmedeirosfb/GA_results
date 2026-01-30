import numpy as np
import random
from random import randint
import pandas as pd
import time
import csv
import matplotlib.pyplot as plt
import os


df = pd.read_csv("ga_calibration_grid.csv", usecols=['nome','mutacao', 'elite', 'generation', 'population_size','step'])
print(df.mutacao[0], df.elite[0],df.generation[0],df.population_size[0],df.step[0])
#input("em espera")
df.elite = df.elite / 100
df.step = df.step / 100
print(df.mutacao[1], df.elite[1],df.generation[1],df.population_size[1],df.step[1])
#input("em espera")
melhor_geral = -1e9
sem_melhora = 0
sem_melhora_imig = 0
sem_melhora_meme = 0
sem_melhora_reset = 0
sem_melhora_intensiva = 0
sem_melhora_total = 0
#for id_rodada, parametros_rodada in df.iterrows():

for ID in range(16):
	melhor_geral = -1e9
	sem_melhora = 0
	sem_melhora_imig = 0
	sem_melhora_meme = 0
	sem_melhora_reset = 0
	sem_melhora_intensiva = 0
	sem_melhora_total = 0
	parametro_mutacao = df.mutacao[ID]
	parametro_elite = df.elite[ID]
	num_generations = df.generation[ID]
	initial_population_size = df.population_size[ID]
	chancestep = df.step[ID]
	stepp = int(chancestep*initial_population_size)

	base, _ = os.path.splitext(df.nome[ID])
	output_name = base + "_PROGRESS.txt"

	#print("parametro mutacao vale", parametro_mutacao)
	#print("parametro_elite vale", parametro_elite)
	#print("num_generations vale", num_generations)
	#print("populationsize vale", initial_population_size)
	#print("chancestep vale", chancestep)



	class Individuo:
		def __init__(self, cromossomo):
			self.cromossomo = cromossomo
			self.fitness = None

		def avaliar(self, demand, pij, tin):
			self.fitness = calc_fitness_individual(self.cromossomo, demand, pij, tin)
			
	def mutacao_memetica(individuo, demT, Pij, TiN_values, indiceG, max_iters=5):
		
		# cópia inicial
		melhor = np.copy(individuo.cromossomo)
		N, T = melhor.shape
		individuo.avaliar(demT, Pij, TiN_values)
		best_fit = individuo.fitness

		# função auxiliar para encontrar inícios dos ciclos
		def encontrar_inicios(linha, duracao):
			inicios = []
			i = 0
			while i < T:
				if linha[i] == 1:
					inicios.append(i)
					i += duracao
				else:
					i += 1
			return inicios

		# função para avaliar sem mexer no indivíduo original
		def avaliar_temp(crom):
			temp = Individuo(np.copy(crom))
			temp.avaliar(demT, Pij, TiN_values)
			return temp.fitness
	
		it = 0
		while it < max_iters:
			bio = random.randint(0, N-1)
			tin = TiN_values[bio]

			inicios = encontrar_inicios(melhor[bio, :], tin)
			if len(inicios) == 0:
				it += 1
				continue

			# pega um ciclo aleatório
			inicio = random.choice(inicios)
			for desloc in [-10,-5,-3, -2, -1, 1, 2, 3, 5, 10]:	# tentar -1 e +1

			#for desloc in [-10, -9, -8, -7, -6, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:	# tentar -1 e +1
				nova_pos = inicio + desloc

				# checar limites com indiceG
				if nova_pos < 0 or nova_pos + tin > T - indiceG:
					continue

				# criar cópia para testar
				novo = np.copy(melhor)

				# remover ciclo antigo
				for k in range(tin):
					novo[bio, inicio+k] = 0

				# checar sobreposição no novo lugar
				ok = True
				for k in range(tin):
					if novo[bio, nova_pos + k] == 1:
						ok = False
						break
				if not ok:
					continue

				# inserir ciclo deslocado
				for k in range(tin):
					novo[bio, nova_pos + k] = 1

				# avaliar
				f_new = avaliar_temp(novo)

				if f_new > best_fit:
					# melhoria aceita!
					best_fit = f_new
					melhor = novo
					individuo.cromossomo = np.copy(melhor)
					individuo.fitness = best_fit
					return individuo	# early exit — uma boa melhoria basta

			it += 1

		# se nada melhorar, retorna original
		return individuo

	#funcao de individuo aelatorio, tentar criar imigrantes
	
	def gerar_individuo_aleatorio(indiceN, indiceT, TiN_values, indiceG):
		indiv = np.zeros((indiceN, indiceT), dtype=int)
		for y in range(indiceN):
			t = 0
			p = random.random()
			while t < indiceT - indiceG:
			# decide se começa um ciclo nesse dia
				if random.random() < p:
					Ty = TiN_values[y]

					# injeta ciclo
					for k in range(Ty):
						if t + k < indiceT:
							indiv[y, t + k] = 1
					t += Ty  # pula o ciclo inteiro
				else:
					t += 1
		return indiv
	#parametro_mutacao = 10	# chance % de mutação por indivíduo
	#parametro_elite = 0.2		# % da elite
	#num_generations = 50		# número de gerações, antes 20
	#initial_population_size = 5000
	#chancestep = 0.05
	#stepp = int(chancestep*initial_population_size)

	# -----------------------------------------------------------------
	# remover duplicados
	# -----------------------------------------------------------------
	def remover_duplicados(pop):
		vistos = set()
		nova = []
		for ind in pop:
			key = tuple(ind.cromossomo.flatten())
			if key not in vistos:
				vistos.add(key)
				nova.append(ind)
		return nova

	# -----------------------------------------------------------------
	# FITNESS
	# -----------------------------------------------------------------
	def calc_fitness_final(individual_schedule, demand_1, pij_1, tin_values_1):
		n_biodigestors = individual_schedule.shape[0]
		horizon_length = individual_schedule.shape[1]

		producao_diaria_total = np.zeros(horizon_length)

		# produção diária
		for i in range(n_biodigestors):
			t = 0
			while t < horizon_length:
				if individual_schedule[i, t] == 1:
					for k, prod in enumerate(pij_1[i]):
						if t + k < horizon_length:
							producao_diaria_total[t + k] += prod
					t += len(pij_1[i])
				else:
					t += 1

		# estoque diário
		estoque = 0.0
		lista_estoques = []
		for t in range(horizon_length):
			disponivel = estoque + producao_diaria_total[t]
			estoque = disponivel - demand_1[t]
			lista_estoques.append(estoque)

		lista_estoques_validos = lista_estoques[indiceF : len(lista_estoques) - indiceG]
		desv_padrao = np.std(lista_estoques_validos)
		
		# desvio padrão para informação (pode comentar se quiser menos prints)
		#desv_padrao = np.std(lista_estoques)
		# print("\nO desvio padrao do individuo eh: \n", desv_padrao)

		# penalizações possíveis (você escolhe o que somar ao fitness)
		soma_dos_negativos = sum([i for i in lista_estoques_validos if i < 0])
		dias_negativos = sum(1 for x in lista_estoques_validos if x < 0)
		if(soma_dos_negativos < 0):
			soma_dos_negativos = soma_dos_negativos * (-1)

		# fitness simples (média do estoque). Ajuste depois para penalizar negativos/flutuações
		print("soma dos negativos vale", soma_dos_negativos)
		print("o resultado seria: ",np.mean(lista_estoques_validos) + soma_dos_negativos)
	
		print("dias negativos vale", dias_negativos)
		

		fitness = np.mean(lista_estoques_validos)
		#print("desv padrao valia antes de retornar",desv_padrao)
		return fitness, desv_padrao, dias_negativos

	def calc_fitness_individual(individual_schedule, demand_1, pij_1, tin_values_1):
		n_biodigestors = individual_schedule.shape[0]
		horizon_length = individual_schedule.shape[1]

		producao_diaria_total = np.zeros(horizon_length)

		# produção diária
		for i in range(n_biodigestors):
			t = 0
			while t < horizon_length:
				if individual_schedule[i, t] == 1:
					for k, prod in enumerate(pij_1[i]):
						if t + k < horizon_length:
							producao_diaria_total[t + k] += prod
					t += len(pij_1[i])
				else:
					t += 1

		# estoque diário
		estoque = 0.0
		lista_estoques = []

		for t in range(horizon_length):
			disponivel = estoque + producao_diaria_total[t]
			estoque = disponivel - demand_1[t]
			lista_estoques.append(estoque)
		
		lista_estoques_validos = lista_estoques[indiceF : len(lista_estoques) - indiceG]

		#variaveis para W1, W2, W3, W4
		n_valid = len(lista_estoques_validos)
		mean_surplus = np.mean(lista_estoques_validos) #w1 ok
		soma_dos_negativos = sum([i for i in lista_estoques_validos if i < 0]) # w2	
		dias_negativos = sum(1 for x in lista_estoques_validos if x < 0)  #w3	
		
		
		soma_dos_negativos = abs(soma_dos_negativos)/n_valid
		dias_negativos = dias_negativos / n_valid		
		
		
		#normalizacao das variaveis
		o = max (mean_surplus, 0) 
		u = soma_dos_negativos
		H = n_valid
		SD = np.std(lista_estoques_validos)
		
		max_estoque = max(lista_estoques_validos)
		min_estoque = min(lista_estoques_validos)
		SD_max = (max_estoque - min_estoque) / 2

		
		overprod = 1 / (o + 1)
		underprod = 1 / (u + 1)
		days = (H - dias_negativos) / H if H > 0 else 0
		stability = (SD_max - SD) / SD_max if SD_max > 0 else 0		
		#if dias_negativos > 0:
			#w1, w2, w3, w4 = 1, 3, 2, 0  # Penalizar mais dias negativos
		#else:
			#w1, w2, w3, w4 = 2, 1, 1, 1  # Balancear outros objetivos
		
		w1, w2, w3, w4 = 1, 2, 0, 0	
		#fitness = overprod * days
		fitness = w1 * overprod + w2 * underprod + w3 * days + w4 * stability
 		
		
	
		#fitness = np.mean(lista_estoques_validos) + soma_dos_negativos + (dias_negativos * dias_negativos) + desv_padrao
	

		#fitness = np.mean(lista_estoques) - soma_dos_negativos
		#if(soma_dos_negativos != 0):
		#	print("soma vale",soma_dos_negativos)
		#	print("media das sobras vale", np.mean(lista_estoques))
		#	print("fitness vale",fitness)

		#	input("Pressione Enter para continuar...")
		#	input("Pressione Enter para continuar...")
		# fitness simples (média do estoque). Ajuste depois para penalizar negativos/flutuações
		#fitness = np.mean(lista_estoques_validos) - soma_dos_negativos + (dias_negativos * dias_negativos) + desv_padrao
		#fitness = np.mean(lista_estoques_validos)

		return fitness

	# -----------------------------------------------------------------
	# ROLETA   # maior fitness → maior chance
	# -----------------------------------------------------------------
	def roleta(populacao, num_selecionados):
		fitness_values = np.array([ind.fitness for ind in populacao], dtype=float)
		soma = np.sum(fitness_values)
		  # maior fitness → maior chance
		if soma == 0:
			probabilities = np.ones(len(populacao)) / len(populacao)
		else:
			probabilities = fitness_values / soma
		selected_indices = np.random.choice(len(populacao), size=num_selecionados, replace=True, p=probabilities)
		return [populacao[i] for i in selected_indices]


	# -----------------------------------------------------------------
	# SELEÇÃO POR TORNEIO (Substitui a Roleta)
	# -----------------------------------------------------------------
	def torneio(populacao, num_selecionados, k):
	
		selecionados = []
		for _ in range(num_selecionados):
			# Sorteia 'k' competidores aleatoriamente da população
			competidores = random.sample(populacao, k)
			
			# O vencedor é o que tiver maior fitness (max)
			# Se seu problema for minimização, use min()
			vencedor = max(competidores, key=lambda ind: ind.fitness)
			
			selecionados.append(vencedor)
			
		return selecionados

	# -----------------------------------------------------------------
	# CROSSOVER POR UMA LINHA (troca apenas 1 biodigestor)
	# -----------------------------------------------------------------
	def crossover(pai, mae, N):

		filho1 = np.copy(pai.cromossomo)
		filho2 = np.copy(mae.cromossomo)

		#trocar apenas uma linha (pouca convergencia)
		idx = random.randint(0, N-1)
		filho1[idx, :] = mae.cromossomo[idx, :]
		filho2[idx, :] = pai.cromossomo[idx, :]

		
		#qnt = random.randint(1, max(1, N//2))

		#linhas = random.sample(range(N), qnt)

		#for idx in linhas:
		#	filho1[idx, :] = mae.cromossomo[idx, :]
		#	filho2[idx, :] = pai.cromossomo[idx, :]

		
		return Individuo(filho1), Individuo(filho2)

	# -----------------------------------------------------------------
	# MUTAÇÃO 
	# -----------------------------------------------------------------
	def mutacao(individual_schedule, N, T, Tin, indiceG):
		novo = np.copy(individual_schedule)
		tentativas = random.randint(1, 3)
		for _ in range(tentativas):
			mutacao_bio = random.randint(0, N-1)
			t = random.randint(0, T-1)
			#print("\n\nBEFORE MUTATION")		
			#print(novo)
			#print("bio sorteado", mutacao_bio)
			#print("T sorteado", t)
			#print("valor do dia",novo[mutacao_bio, t])
			if novo[mutacao_bio, t] == 1:
				# CASE 1: remover o ciclo inteiro onde 't' está
				inicios = []
				i = 0
				while i < T:
					if novo[mutacao_bio, i] == 1:
						inicios.append(i)
						i += Tin[mutacao_bio]
					else:
						i += 1

				for inicio in inicios:
					if inicio <= t < inicio + Tin[mutacao_bio]:
						for k in range(Tin[mutacao_bio]):
							if inicio + k < T:
								novo[mutacao_bio, inicio+k] = 0
						break
			else:
				# CASE 2: tentar adicionar novo ciclo (permitido iniciar nos primeiros dias,
				# mas não permitir iniciar se não couber antes do T - indiceG)
				if t + Tin[mutacao_bio] <= T - indiceG:
					pode = True
					for k in range(Tin[mutacao_bio]):
						if novo[mutacao_bio, t+k] == 1:
							pode = False
							break
					if pode:
						for k in range(Tin[mutacao_bio]):
							novo[mutacao_bio, t+k] = 1
			#print("after mutation")
			#print(novo)

		return novo

	# -----------------------------------------------------------------
	# MUTAÇÃO LOCAL, VIZINHANÇA MENOR
	# -----------------------------------------------------------------
	def mutacao_global_simples(individual_schedule, N, T, Tin, indiceG):
		"""
		Move um ciclo inteiro dentro da MESMA linha do biodigestor,
		sem quebrar o bloco e sem tocar em outros ciclos.
		"""
		novo = np.copy(individual_schedule)

		# escolher biodigestor aleatório
		bio = random.randint(0, N - 1)
		dur = Tin[bio]
		linha = novo[bio]

    # --- encontrar ciclos existentes ---
		def encontrar_inicios(linha, duracao):
		    inicios = []
		    i = 0
		    while i < T:
		        if linha[i] == 1:
		            inicios.append(i)
		            i += duracao
		        else:
		            i += 1
		    return inicios

		inicios = encontrar_inicios(linha, dur)

		# se a linha não tem ciclos, nada a mover
		if len(inicios) == 0:
			return novo

    # escolher ciclo para mover
		inicio_original = random.choice(inicios)

    # remover ciclo
		for k in range(dur):
			if inicio_original + k < T:
				novo[bio, inicio_original + k] = 0

		# --- encontrar todos os slots válidos para recolocar ---
		slots = []
		ultimo_inicio = T - dur - indiceG

		for s in range(0, ultimo_inicio + 1):
			# verificar se cabe sem colisão com outros ciclos
			if np.all(novo[bio, s:s+dur] == 0):
				slots.append(s)

		# se não há outro lugar para colocar → desfaz, sem mutação
		if len(slots) == 0:
			# recolocar no original
			for k in range(dur):
				novo[bio, inicio_original + k] = 1
			return novo

		# remover a posição original dos candidatos
		if inicio_original in slots and len(slots) > 1:
			slots.remove(inicio_original)

		# escolher novo início aleatório
		novo_inicio = random.choice(slots)

		# escrever ciclo na nova posição
		for k in range(dur):
			novo[bio, novo_inicio + k] = 1
			#print("mutacao novaaaaaaaaaaaaa")
		return novo

	def mutacao_colapso(linha, duracao):
		# pega todos os inicios detectados
		inicios = encontrar_inicios(linha, duracao)

		if len(inicios) <= 1:
			return linha  # já está OK

		# escolhe media ou um inicio aleatorio
		novo_inicio = random.choice(inicios)

		# apaga tudo
		linha[:] = 0

		# insere um ciclo só no novo início
		for k in range(duracao):
			if novo_inicio + k < len(linha):
				linha[novo_inicio + k] = 1

		return linha

	#*****************************************************************
	#mutacao_best_fit 
	#*****************************************************************
	def mutacao_best_fit(individuo, demT, Pij, TiN_values, indiceG):
		"""
		- Remove um ciclo de um biodigestor		- Testa TODAS as posições possíveis para recolocar		- Insere na melhor posição encontrada.
		"""

		crom = np.copy(individuo.cromossomo)
		N, T = crom.shape

		# 1. Escolher biodigestor aleatório
		bio = random.randint(0, N - 1)
		dur = TiN_values[bio]

		# Função auxiliar: encontrar inícios do ciclo
		def encontrar_inicios(linha, duracao):
			inicios = []
			t = 0
			while t < T:
				if linha[t] == 1:
					inicios.append(t)
					t += duracao
				else:
					t += 1
			return inicios

		inicios = encontrar_inicios(crom[bio], dur)

		# Se não tiver ciclo, não faz nada
		if len(inicios) == 0:
			return crom

		# Sorteia um dos ciclos existentes
		inicio_atual = random.choice(inicios)

		# 2. Remover ciclo atual
		for k in range(dur):
			crom[bio, inicio_atual + k] = 0

		# 3. Testar todas as posições válidas
		melhor_fit = -1e18
		melhor_pos = None

		for pos in range(0, T - dur - indiceG + 1):

			# verificar sobreposição
			conflito = False
			for k in range(dur):
				if crom[bio, pos + k] == 1:
					conflito = True
					break
			if conflito:
				continue

			# testar inserção
			crom_temp = np.copy(crom)
			for k in range(dur):
				crom_temp[bio, pos + k] = 1

			# avaliar
			temp = Individuo(crom_temp)
			temp.avaliar(demT, Pij, TiN_values)
			f = temp.fitness

			if f > melhor_fit:
				melhor_fit = f
				melhor_pos = pos

		# 4. Se não encontrou posição melhor, volta ao original
		if melhor_pos is None:
			for k in range(dur):
				crom[bio, inicio_atual + k] = 1
			return crom

		# 5. Caso encontre: aplicar a melhor posição
		for k in range(dur):
			crom[bio, melhor_pos + k] = 1

		return crom
	#*****************************************************************
	#mutacao_ 
	#*****************************************************************
	def mutacao_multi_bio_global(individual_schedule, TiN_values, indiceG):
		"""
		Move ciclos de 2 ou 3 biodigestores simultaneamente.
		Resolve conflitos onde Bio A bloqueia Bio B.
		"""

		# Obter cromossomo
		if hasattr(individual_schedule, 'cromossomo'):
			crom = np.copy(individual_schedule.cromossomo)
		else:
			crom = np.copy(individual_schedule)

		N, T = crom.shape

		# Quantos biodigestores vamos mover simultaneamente?
		k = 2 if random.random() < 0.95 else 3
		k = min(k, N)

		bios = random.sample(range(N), k)

		# Deslocamentos aleatórios (-7 a -1 ou +1 a +7)
		deslocs = {}
		for bio in bios:
			d = random.randint(1, 7)
			if random.random() < 0.5:
				d = -d
			deslocs[bio] = d

		# Achar todos os ciclos de um biodigestor
		def encontrar_inicios(linha, duracao):
			inicios = []
			t = 0
			while t < T:
				if linha[t] == 1:
					inicios.append(t)
					t += duracao
				else:
					t += 1
			return inicios

		novo = np.copy(crom)
		inicios_escolhidos = {}

		# Remover ciclos originais
		for bio in bios:
			tin = TiN_values[bio]
			inicios = encontrar_inicios(novo[bio], tin)

			if not inicios:		# Bio sem ciclo → cancela mutação
				return crom

			inicio = random.choice(inicios)
			inicios_escolhidos[bio] = inicio

			# Remover via slicing
			novo[bio, inicio : inicio + tin] = 0

		# Validar novas posições
		for bio in bios:
			tin = TiN_values[bio]
			origem = inicios_escolhidos[bio]
			destino = origem + deslocs[bio]

			# Limites globais
			if destino < 0 or destino + tin > (T - indiceG):
				return crom

			# Colisão com outros ciclos
			if np.sum(novo[bio, destino : destino + tin]) > 0:
				return crom

		# Aplicar mutação simultânea
		for bio in bios:
			tin = TiN_values[bio]
			destino = inicios_escolhidos[bio] + deslocs[bio]
			novo[bio, destino : destino + tin] = 1

		return novo

	def busca_local_intensiva(individuo, demT, Pij, TiN_values, indiceG, max_iter=20):
		melhor = np.copy(individuo.cromossomo)
		melhor_fit = individuo.fitness
		N, T = melhor.shape
		
		for _ in range(max_iter):
			# Tentar diferentes tipos de movimento
			movimentos = [
				mutacao_global_simples(melhor, N, T, TiN_values, indiceG),
				mutacao_multi_bio_global(Individuo(melhor), TiN_values, indiceG),
				mutacao_best_fit(Individuo(melhor), demT, Pij, TiN_values, indiceG)
			]
			
			for movimento in movimentos:
				temp = Individuo(movimento)
				temp.avaliar(demT, Pij, TiN_values)
				if temp.fitness > melhor_fit:
					melhor = movimento
					melhor_fit = temp.fitness
					break  # Aceita a primeira melhoria
		
		individuo.cromossomo = melhor
		individuo.fitness = melhor_fit
		return individuo


	# -----------------------------------------------------------------
	# LEITURA DE DADOS
	# -----------------------------------------------------------------

	start_time = time.time()

	demT = np.array([])
	Pij = []
	
	with open("revistaB_sazonal_5_6_7.txt", "r") as f:
		values = f.readline().strip().split()
		indiceN, indiceT, indiceG = map(int, values)
		indiceF = indiceG + 1
		print("Number of Biodigesters:", indiceN)
		print("Number of Days:", indiceT)
		print("Size of G:", indiceG)
		print("Size of F:", indiceF)

		values = f.readline().strip().split()
		for val in values[:indiceT]:
			demT = np.append(demT, int(val))
		print("Demand array length:", len(demT))

		TiN_values = np.empty(indiceN, dtype=int)
		values = f.readline().strip().split()
		for val in values[:indiceN]:
			TiN_values = np.array([int(val) for val in values[:indiceN]], dtype=int)
		print("Ciclos dos biodigestores:", TiN_values)

		for line in f:
			row = line.strip().split()
			Pij.append([int(item) for item in row])

	f.close()

	# -----------------------------------------------------------------
	# POPULAÇÃO INICIAL
	# -----------------------------------------------------------------
	melhor_cromossomo_global = None
	melhor_fitness_global = -9999999
	
	horizon = np.zeros((initial_population_size, indiceN, indiceT), dtype=int)
	
	chance = chancestep #inicia com 5
	cont = 0

	for p in range(initial_population_size):
		cont = cont + 1
		
		# calcula a chance do bloco atual (10%, 20%, 30%, …)
		
		
		if chance > 1.0:
			chance = 1.0  # garantir que não ultrapasse 100%
		#print("chance vale", chance)
		#print("estamos no individuo ",p)

		for y in range(indiceN):  # para cada biodigestor
			t = 0
			while t < (indiceT - indiceG):
				sort = random.random()				
				

				if sort < chance:  # decide ativar ou não o biodigestor

					
					for x in range(TiN_values[y]):
						if t <= indiceT:
							horizon[p][y][t] = 1
							t += 1
						else:
							break
				else:			
					horizon[p][y][t] = 0
					t += 1
		
		if(cont==stepp):
			chance = chance + chancestep
			cont = 0

	populacao = [Individuo(horizon[p]) for p in range(initial_population_size)]
	for ind in populacao:
		ind.avaliar(demT, Pij, TiN_values)

	#print(f"Indivíduo 0: Fitness = {populacao[0].fitness}")
	#print(populacao[0].cromossomo)

	#for i, ind in enumerate(populacao):
		#print(f"Individuo {i}: Fitness = {ind.fitness}")
		#print(ind.cromossomo)

	
	#input("em espera")	
	#input("em espera")	
	# -----------------------------------------------------------------
	# LOOP DE GERAÇÕES DO GA
	# -----------------------------------------------------------------
	acabou_de_resetar = False
	gen = 0
	MAX_GEN = 200
	MAX_NO_IMPROVE = 50	
	while gen < MAX_GEN:
	#for gen in range(num_generations):
		# garantir que todos tenham fitness calculado antes de ordenar / selecionar
		#for ind in populacao:
			#if ind.fitness is None: #to tentando melhorar desemepenho, entaot tirei
				#ind.avaliar(demT, Pij, TiN_values)

		# ordenar por fitness (maior primeiro)
		populacao.sort(key=lambda ind: ind.fitness, reverse=True)
		#print("tamanho da populacao vale", len(populacao))
		best = max(populacao, key=lambda ind: ind.fitness)
		if (not acabou_de_resetar) and (best.fitness > melhor_geral + 1e-6):
			melhor_geral = best.fitness
			sem_melhora = 0
			parametro_mutacao = df.mutacao[ID]
			sem_melhora_imig = 0
			sem_melhora_meme = 0
			sem_melhora_reset = 0
			sem_melhora_intensiva = 0
			sem_melhora_total = 0
		else:
			sem_melhora += 1
			sem_melhora_imig += 1
			sem_melhora_meme += 1
			sem_melhora_reset += 1
			sem_melhora_intensiva += 1
			sem_melhora_total += 1
		
		if sem_melhora > 10:
			parametro_mutacao = min(parametro_mutacao * 1.1, 80)  # até 80%
			
			sem_melhora = 0
			print("parametro mutacao alterado", parametro_mutacao)
			
		# elite
		elite_size = int(parametro_elite * len(populacao))		
		elite = populacao[:elite_size]
		
		if elite[0].fitness > melhor_fitness_global:
			melhor_fitness_global = elite[0].fitness
			melhor_cromossomo_global = np.copy(elite[0].cromossomo)

		# seleção
		num_children = len(populacao) - len(elite)
		if num_children <= 0:
			break
		
		#pais_roleta = roleta(populacao, num_children)
		pais_selecionados = torneio(populacao, num_children, 2)

		# crossover (garantir número suficiente de filhos mesmo se num_children ímpar)
		filhos = []
		while len(filhos) < num_children:
			#a = random.randrange(len(pais_roleta))
			#b = random.randrange(len(pais_roleta))
			#f1, f2 = crossover(pais_roleta[a], pais_roleta[b], indiceN)
			a = random.randrange(len(pais_selecionados))
			b = random.randrange(len(pais_selecionados))
			f1, f2 = crossover(pais_selecionados[a], pais_selecionados[b], indiceN)
			f1.avaliar(demT, Pij, TiN_values)
			f2.avaliar(demT, Pij, TiN_values)
			filhos.extend([f1, f2])

		filhos = filhos[:num_children]

		# mutação + avaliação dos filhos
		for ind in filhos:
			aleatorio = random.randint(1, 100)
			
			if aleatorio <= parametro_mutacao:
				r = random.random()
				if r < 0.25:
					ind.cromossomo = mutacao(ind.cromossomo, indiceN, indiceT, TiN_values, indiceG)
					#ind.avaliar(demT, Pij, TiN_values)
				elif r < 0.50:
					ind.cromossomo = mutacao_global_simples(ind.cromossomo, indiceN, indiceT, TiN_values, indiceG)
					#ind.avaliar(demT, Pij, TiN_values)
				elif r < 0.75:
					ind.cromossomo = mutacao_multi_bio_global(ind, TiN_values, indiceG)
					#ind = mutacao_memetica(ind, demT, Pij, TiN_values, indiceG)
				else:
					ind.cromossomo = mutacao_best_fit(ind, demT, Pij, TiN_values, indiceG)
					#ind.avaliar(demT, Pij, TiN_values)
				ind.avaliar(demT, Pij, TiN_values)
				

				#print("mutacao nova")

				

		# formar nova população (elite + filhos necessários)
		populacao = elite + filhos
		#print(populacao)
		
		num_imigrantes = int(initial_population_size * 0.05) 

		#***************************************************#
		#INSERIR X IMIGRANTES A CADA ITERACAO **************#
		#***************************************************#

		#if num_imigrantes > 999999999999: #if num_imigrantes > 0:
		# Ordena para garantir que mataremos os piores (fitness menor está no fim da lista se reverse=True)
			#populacao.sort(key=lambda ind: ind.fitness, reverse=True) 

			#for i in range(1, num_imigrantes + 1):
		# Gera novo
			#	crom = gerar_individuo_aleatorio(indiceN, indiceT, TiN_values, indiceG)
			#	ind = Individuo(crom)
			#	ind.avaliar(demT, Pij, TiN_values)

		# Substitui o pior (índice negativo acessa o fim da lista)
			#	populacao[-i] = ind
		
		#***************************************************#
		#trocar proletários **************#
		#***************************************************#
		if sem_melhora_imig == 15: # por exemplo
			print("nova populacao")
			new_pop = []
			#melhor_individuo = elite[0]
			#new_pop.append(melhor_individuo)

			
			qtd = int(0.10 * len(populacao))  #
			elite_manter = populacao[:qtd]
			num_novos = initial_population_size - qtd
			new_pop.extend(elite_manter)
			for _ in range(num_novos):

			#novos = []
			#for _ in range(qtd):
			#for _ in range(initial_population_size - 1):
				crom = gerar_individuo_aleatorio(indiceN, indiceT, TiN_values, indiceG)
				#print(crom)
				ind = Individuo(crom)
				ind.avaliar(demT, Pij, TiN_values)
				# substitui os piores indivíduos
				#print(ind)
				new_pop.append(ind)
				
			#sem_melhora_imig = 0
			populacao = new_pop			
			populacao.sort(key=lambda ind: ind.fitness, reverse=True)
			elite = populacao[:elite_size]
			sem_melhora_imig = 0
		
			#populacao.sort(key=lambda ind: ind.fitness)
			#for i in range(qtd):		
				#populacao[i] = novos[i]
		
			#print(">>> Depois da imigração:")
			#print("len(populacao) =", len(populacao))
			#print("Top 5 fitness:", [ind.fitness for ind in populacao[:5]])
			#print("Bottom 5 fitness:", [ind.fitness for ind in populacao[-5:]])
		
	

		#best = max(populacao, key=lambda ind: ind.fitness)
		#print(f"Geração {gen}: Melhor fitness = {best.fitness}")

		if sem_melhora_intensiva == 30:
			print("BUSCA LOCAL INTENSIVA")
			for i in range(min(3, elite_size)):
					elite[i] = busca_local_intensiva(elite[i], demT, Pij, TiN_values, indiceG)
			#sem_melhora = 0
			#sem_melhora_imig = 0
			#sem_melhora_meme = 0
			#sem_melhora_reset = 0
			sem_melhora_intensiva = 0
		
		#***************************************************#
		#deletar toda a populacao
		#***************************************************#
		if sem_melhora_reset >= 40:
			
			print(">>> INICIANDO PROTOCOLO DE RESET TOTAL (KILL ALL).")
			
			nova_populacao = []	
			
			for _ in range(initial_population_size -1):
				crom = gerar_individuo_aleatorio(indiceN, indiceT, TiN_values, indiceG)
				ind = Individuo(crom)
				ind.avaliar(demT, Pij, TiN_values)
				#print("ind.fitness vale", ind.fitness)
				nova_populacao.append(ind)
			
			populacao = nova_populacao
			if melhor_cromossomo_global is not None:
				ind_best = Individuo(np.copy(melhor_cromossomo_global))
				ind_best.avaliar(demT, Pij, TiN_values)
				populacao[-1] = ind_best
				print(f">>> Melhor Global Reintroduzido (FO={melhor_fitness_global})")
			# Reseta TODAS as métricas de controle para a nova "Era"
			#melhor_geral = -1e9 
			sem_melhora = 0
			sem_melhora_imig = 0
			sem_melhora_meme = 0
			sem_melhora_reset = 0
			sem_melhora_intensiva = 0
			acabou_de_resetar = True
			print(">>> População regenerada 100% aleatória. Nova busca iniciada.\n")
			#input("espera")

			

		#if sem_melhora_meme == 10:
			#print("memetico ativado")
			#for i in range(min(5, elite_size)):
				#elite[0] = memetic_shift(elite[0], demT, Pij, TiN_values, indiceG)
				#mel = memetic_shift(elite[i], demT, Pij, TiN_values, indiceG)	
				#if mel.fitness > elite[i].fitness:
					#elite[i] = mel
					#populacao[i] = mel
	
				#elite[i] = memetic_shift(elite[i], demT, Pij, TiN_values, indiceG)			
			#sem_melhora_meme = 0

		
		populacao.sort(key=lambda ind: ind.fitness, reverse=True)
		#print("tamanho da elite vale:", elite_size)
		elite = populacao[:elite_size]		
		fitness_values_elite = np.array([ind.fitness for ind in elite], dtype=float)
		mean_fit_elite = np.mean(fitness_values_elite)

		if abs(populacao[0].fitness - mean_fit_elite)<  1e-1:

			populacao = remover_duplicados(populacao)

			while len(populacao) < initial_population_size:
				crom = gerar_individuo_aleatorio(indiceN, indiceT, TiN_values, indiceG)
				ind = Individuo(crom)
				ind.avaliar(demT, Pij, TiN_values)
				populacao.append(ind)
		best = max(populacao, key=lambda ind: ind.fitness)
		print(f"Geração {gen}: Melhor fitness = {best.fitness}")

		populacao.sort(key=lambda ind: ind.fitness, reverse=True)
		elite = populacao[:elite_size]
		fitness_values = np.array([ind.fitness for ind in populacao], dtype=float)
		fitness_values_elite = np.array([ind.fitness for ind in elite], dtype=float)

		mean_fit = np.mean(fitness_values)
		mean_fit_elite = np.mean(fitness_values_elite)

		

		with open(output_name, "a") as f:
			if gen == 0:  # write header only once
				f.write("gen\tBest_Fitness\tMean_Fitness\tMean_Fitness_Elite\n")
			f.write(f"{gen}\t{best.fitness:.4f}\t{mean_fit:.4f}\t{mean_fit_elite:.4f}\n")

		print("SEM MELHORA VALE",sem_melhora_total)
		if sem_melhora_total >= MAX_NO_IMPROVE:
			print(">>> Estagnação total detectada. Encerrando otimização.")
			break
		gen += 1
		

	# -----------------------------------------------------------------
	# RESULTADO FINAL
	# -----------------------------------------------------------------
	dz= pd.read_csv(output_name, sep="\t")
	plt.figure(figsize=(10,6))
	plt.plot(dz["gen"], dz["Best_Fitness"], label="Melhor Fitness", linewidth=2)
	plt.plot(dz["gen"], dz["Mean_Fitness"], label="Fitness Médio", linestyle="--")
	plt.plot(dz["gen"], dz["Mean_Fitness_Elite"], label="Fitness Médio (Elite)", linestyle=":")
	plt.xlabel("gen")
	plt.ylabel("Fitness Normalizado")
	plt.title("Convergência do Algoritmo Genético")
	plt.legend()
	plt.grid(True, linestyle="--", alpha=0.7)
	plt.tight_layout()

	fig_name = df.nome[ID].replace(".txt", ".png")
	plt.savefig(fig_name, dpi=300, bbox_inches="tight")
	plt.close()

	#plt.show()
	best = max(populacao, key=lambda ind: ind.fitness)
	#print("\nMelhor indivíduo final:")
	#print(best.cromossomo)
	#print("Fitness:", best.fitness)

	novo_fitness, desv, dias_neg = calc_fitness_final(best.cromossomo, demT, Pij, TiN_values)
	best.fitness = novo_fitness
	end_time = time.time()
	#print("TIME IS", end_time - start_time)
	tempo =  end_time - start_time

	print("\nMelhor indivíduo final:")
	print(best.cromossomo)
	print("Fitness:", best.fitness)
	#print("desvio padrao eh: ")
	#print(desv)
	
	f = open(df.nome[ID], "w")
	f.write("\nMelhor indivíduo final: \n")
	np.savetxt(f, best.cromossomo, fmt="%d")  
	f.write(f"\nFitness: {best.fitness:.4f}\n")
	f.write(f"Desvio padrão: {desv:.4f}\n")
	f.write(f"Tempo de execução: {tempo:.2f} segundos\n")
	f.write(f"dias negativos: {dias_neg:.2f} \n")
	f.write(f"Numero de geracoes: {gen} \n")

	df.loc[ID, "FO_1"] = best.fitness
	df.loc[ID, "Tempo_1"] = tempo
	df.loc[ID, "Desv_1"] = desv
	df.loc[ID, "dias_neg"] = dias_neg
	df.loc[ID, "Gen"] = gen



	
	f.write(f"parametro mutacao vale: {int(parametro_mutacao)}\n")
	f.write(f"parametro_elite vale: {float(parametro_elite)}\n")
	f.write(f"num_generations vale: {int(num_generations)}\n")
	f.write(f"population_size vale: {int(initial_population_size)}\n")
	f.write(f"chancestep vale: {float(chancestep)}\n")

		# salva de volta no CSV
	df.to_csv("ga_calibration_results2.csv", index=False)
	f.close()
	


