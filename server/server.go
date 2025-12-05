package main

import (
	"bytes"
	"encoding/base64"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"image"
	"image/color"
	"image/png"
	"log"
	"math"
	"net"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/shirou/gopsutil/v3/cpu"
	"github.com/shirou/gopsutil/v3/mem"
	"gonum.org/v1/gonum/mat"
)

const (
	MAX_WORKERS    = 4
	PORT           = "7776"
	MIN_ERROR      = 0.0001
	MAX_ITERATIONS = 5
	TOL_REQUISITO  = 1e-4
	MIN_ITERATIONS = 10
	CPU_LIMIT      = 90.0 // Aumentado para 95% - ATENÇÃO: pode ser arriscado em sistemas com pouca RAM
	MEM_LIMIT      = 90.0 // Aumentado para 95% - ATENÇÃO: pode causar swap se exceder
	MIN_DIV        = 1e-12
)

var (
	requestQueue         = make(chan JobRequest, 100)
	workerWg             sync.WaitGroup
	mu                   sync.Mutex
	baseDir              string
	rootDir              string
	testeJSONPath        string
	performanceCSV       *os.File
	performanceCSVWriter *csv.Writer
	performanceCSVMutex  sync.Mutex
	closeProfiler        = make(chan bool)
)

type JobRequest struct {
	Payload Payload
	Conn    net.Conn
}

type Payload struct {
	Username  string `json:"username"`
	Algorithm string `json:"algorithm"`
	Model     string `json:"model"`
	Signal    string `json:"signal"`
	Idx       int    `json:"idx"`
}

type Response struct {
	Type    string       `json:"type"`
	Payload ResponseData `json:"payload"`
}

type ResponseData struct {
	Header ResponseHeader `json:"header"`
	Image  string         `json:"image"`
}

type ResponseHeader struct {
	Username  string  `json:"username"`
	Index     int     `json:"index"`
	Algorithm string  `json:"algorithm"`
	Model     string  `json:"model"`
	Signal    string  `json:"signal"`
	StartDT   string  `json:"start_dt"`
	EndDT     string  `json:"end_dt"`
	Size      string  `json:"size"`
	Iters     int     `json:"iters"`
	Time      float64 `json:"time"`
}

type HistoryEntry struct {
	Algorithm    string  `json:"algorithm"`
	Model        string  `json:"model"`
	Signal       string  `json:"signal"`
	Time         float64 `json:"time"`
	CPUUsed      float64 `json:"cpu_used"`
	MemUsedBytes int64   `json:"mem_used_bytes"`
}

func init() {
	// Determina diretórios base
	// Tenta obter diretório do executável primeiro
	execPath, err := os.Executable()
	if err != nil {
		// Se falhar, usa diretório atual
		execPath, _ = os.Getwd()
	}
	baseDir = filepath.Dir(execPath)

	// Se baseDir contém "server", assume que rootDir é o pai
	// Caso contrário, tenta encontrar o diretório raiz do projeto
	if filepath.Base(baseDir) == "server" {
		rootDir = filepath.Dir(baseDir)
	} else {
		// Tenta encontrar teste.json subindo diretórios
		wd, _ := os.Getwd()
		rootDir = findRootDir(wd)
	}

	testeJSONPath = filepath.Join(rootDir, "teste.json")

	// Inicializa CSV de performance
	initPerformanceCSV()
}

// initPerformanceCSV inicializa o arquivo CSV de performance
func initPerformanceCSV() {
	relatorioDir := filepath.Join(baseDir, "relatorio")
	os.MkdirAll(relatorioDir, 0755)

	timestamp := time.Now().Unix()
	csvPath := filepath.Join(relatorioDir, fmt.Sprintf("performance-relatorio_%d.csv", timestamp))

	var err error
	performanceCSV, err = os.Create(csvPath)
	if err != nil {
		log.Printf("[ERRO] Não foi possível criar CSV de performance: %v", err)
		return
	}

	performanceCSVWriter = csv.NewWriter(performanceCSV)

	// Escreve cabeçalho
	performanceCSVWriter.Write([]string{"Measured at   ", "CPU usage   ", "Memory usage", "Server"})
	performanceCSVWriter.Flush()

	log.Printf("[INFO] CSV de performance criado: %s", csvPath)
}

// writePerformanceLog escreve uma linha no CSV de performance (thread-safe)
func writePerformanceLog(timestamp string, cpuPercent, memPercent float64) {
	performanceCSVMutex.Lock()
	defer performanceCSVMutex.Unlock()

	if performanceCSVWriter == nil {
		return
	}

	cpuStr := fmt.Sprintf("    %.1f%%", cpuPercent)
	memStr := fmt.Sprintf("    %.1f%%", memPercent)

	performanceCSVWriter.Write([]string{timestamp, cpuStr, memStr, "Go"})
	performanceCSVWriter.Flush()
}

// profilerWorker monitora CPU e RAM continuamente e escreve no CSV
func profilerWorker() {
	ticker := time.NewTicker(500 * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case <-closeProfiler:
			return
		case <-ticker.C:
			timestamp := time.Now().Format("2006-01-02 15:04:05")

			cpuPercent, err := cpu.Percent(0, false)
			if err != nil {
				log.Printf("[ERRO] Erro ao obter CPU: %v", err)
				continue
			}

			memInfo, err := mem.VirtualMemory()
			if err != nil {
				log.Printf("[ERRO] Erro ao obter memória: %v", err)
				continue
			}

			cpuUsage := 0.0
			if len(cpuPercent) > 0 {
				cpuUsage = cpuPercent[0]
			}

			writePerformanceLog(timestamp, cpuUsage, memInfo.UsedPercent)
		}
	}
}

// findRootDir procura o diretório raiz procurando por teste.json
func findRootDir(startDir string) string {
	dir := startDir
	for {
		testPath := filepath.Join(dir, "teste.json")
		if _, err := os.Stat(testPath); err == nil {
			return dir
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			// Chegou na raiz do sistema de arquivos
			break
		}
		dir = parent
	}
	// Se não encontrou, retorna o diretório atual
	return startDir
}

// applySignalGain aplica ganho ao sinal conforme fórmula do Python
func applySignalGain(g []float64) []float64 {
	S := len(g)
	gOut := make([]float64, S)
	for l := 0; l < S; l++ {
		gain := 100.0 + (1.0/20.0)*float64(l+1)*math.Sqrt(float64(l+1))
		gOut[l] = g[l] * gain
	}
	return gOut
}

// loadCSVMatrix carrega uma matriz de um arquivo CSV
func loadCSVMatrix(filename string) (*mat.Dense, error) {
	file, err := os.Open(filename)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return nil, err
	}

	rows := len(records)
	if rows == 0 {
		return nil, fmt.Errorf("arquivo vazio")
	}

	cols := len(records[0])
	data := make([]float64, 0, rows*cols)

	for _, record := range records {
		for _, val := range record {
			f, err := strconv.ParseFloat(strings.TrimSpace(val), 32)
			if err != nil {
				return nil, err
			}
			data = append(data, float64(f))
		}
	}

	return mat.NewDense(rows, cols, data), nil
}

// loadCSVVector carrega um vetor de um arquivo CSV
func loadCSVVector(filename string) ([]float64, error) {
	file, err := os.Open(filename)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return nil, err
	}

	vector := make([]float64, 0)
	for _, record := range records {
		for _, val := range record {
			f, err := strconv.ParseFloat(strings.TrimSpace(val), 32)
			if err != nil {
				return nil, err
			}
			vector = append(vector, float64(f))
		}
	}

	return vector, nil
}

// reconstructCGNR implementa o algoritmo CGNR
func reconstructCGNR(H *mat.Dense, g []float64, maxIterations int, tol float64) ([]float64, int, float64) {
	m, n := H.Dims()

	f := mat.NewVecDense(n, nil)
	gVec := mat.NewVecDense(len(g), g)

	// r = g - H*f
	r := mat.NewVecDense(m, nil)
	Hf := mat.NewVecDense(m, nil)
	Hf.MulVec(H, f)
	r.SubVec(gVec, Hf)

	// z = H^T * r
	z := mat.NewVecDense(n, nil)
	z.MulVec(H.T(), r)

	p := mat.NewVecDense(n, nil)
	p.CopyVec(z)

	initialResidualNorm := mat.Norm(r, 2)
	numberIterations := 0

	for i := 0; i < maxIterations; i++ {
		// w = H * p
		w := mat.NewVecDense(m, nil)
		w.MulVec(H, p)

		// z_dot = z^T * z
		zDot := mat.Dot(z, z)
		// w_dot = w^T * w
		wDot := mat.Dot(w, w) + MIN_DIV

		alpha := zDot / wDot

		// f_new = f + alpha * p
		fNew := mat.NewVecDense(n, nil)
		fNew.CopyVec(f)
		fNew.AddScaledVec(fNew, alpha, p)

		// r_new = r - alpha * w
		rNew := mat.NewVecDense(m, nil)
		rNew.CopyVec(r)
		rNew.AddScaledVec(rNew, -alpha, w)

		// z_new = H^T * r_new
		zNew := mat.NewVecDense(n, nil)
		zNew.MulVec(H.T(), rNew)

		zNewDot := mat.Dot(zNew, zNew)
		beta := zNewDot / (zDot + MIN_DIV)

		// p_new = z_new + beta * p
		pNew := mat.NewVecDense(n, nil)
		pNew.CopyVec(zNew)
		pNew.AddScaledVec(pNew, beta, p)

		currentResidualNorm := mat.Norm(rNew, 2)
		relativeError := currentResidualNorm / (initialResidualNorm + MIN_DIV)

		f = fNew
		r = rNew
		z = zNew
		p = pNew
		numberIterations = i + 1

		if numberIterations >= MIN_ITERATIONS && relativeError < tol {
			break
		}
	}

	// Calcula erro final
	finalResidual := mat.NewVecDense(m, nil)
	HfFinal := mat.NewVecDense(m, nil)
	HfFinal.MulVec(H, f)
	finalResidual.SubVec(gVec, HfFinal)
	finalError := mat.Norm(finalResidual, 2) / (mat.Norm(gVec, 2) + MIN_DIV)

	// Converte para slice
	result := make([]float64, n)
	for i := 0; i < n; i++ {
		result[i] = f.AtVec(i)
	}

	return result, numberIterations, finalError
}

// reconstructCGNE implementa o algoritmo CGNE
func reconstructCGNE(H *mat.Dense, g []float64, maxIterations int, tol float64) ([]float64, int, float64) {
	m, n := H.Dims()

	f := mat.NewVecDense(n, nil)
	gVec := mat.NewVecDense(len(g), g)

	// r = g - H*f
	r := mat.NewVecDense(m, nil)
	Hf := mat.NewVecDense(m, nil)
	Hf.MulVec(H, f)
	r.SubVec(gVec, Hf)

	// p = H^T * r
	p := mat.NewVecDense(n, nil)
	p.MulVec(H.T(), r)

	initialResidualNorm := mat.Norm(r, 2)
	finalIterations := 0

	for i := 0; i < maxIterations; i++ {
		// Hp = H * p
		Hp := mat.NewVecDense(m, nil)
		Hp.MulVec(H, p)

		alphaNum := mat.Dot(r, r)
		alphaDen := mat.Dot(Hp, Hp) + MIN_DIV

		if alphaDen < MIN_DIV {
			break
		}

		alpha := alphaNum / alphaDen

		// f_new = f + alpha * p
		fNew := mat.NewVecDense(n, nil)
		fNew.CopyVec(f)
		fNew.AddScaledVec(fNew, alpha, p)

		// r_new = r - alpha * Hp
		rNew := mat.NewVecDense(m, nil)
		rNew.CopyVec(r)
		rNew.AddScaledVec(rNew, -alpha, Hp)

		betaNum := mat.Dot(rNew, rNew)
		betaDen := mat.Dot(r, r) + MIN_DIV
		beta := betaNum / betaDen

		// p_new = H^T * r_new + beta * p
		pNew := mat.NewVecDense(n, nil)
		HT_rNew := mat.NewVecDense(n, nil)
		HT_rNew.MulVec(H.T(), rNew)
		pNew.CopyVec(HT_rNew)
		pNew.AddScaledVec(pNew, beta, p)

		currentResidualNorm := mat.Norm(rNew, 2)
		relativeError := currentResidualNorm / (initialResidualNorm + MIN_DIV)

		f = fNew
		r = rNew
		p = pNew
		finalIterations = i + 1

		if finalIterations >= MIN_ITERATIONS && relativeError < tol {
			break
		}
	}

	// Calcula erro final
	finalResidual := mat.NewVecDense(m, nil)
	HfFinal := mat.NewVecDense(m, nil)
	HfFinal.MulVec(H, f)
	finalResidual.SubVec(gVec, HfFinal)
	finalError := mat.Norm(finalResidual, 2) / (mat.Norm(gVec, 2) + MIN_DIV)

	// Converte para slice
	result := make([]float64, n)
	for i := 0; i < n; i++ {
		result[i] = f.AtVec(i)
	}

	return result, finalIterations, finalError
}

// normalizeImage normaliza os valores para 0-255
func normalizeImage(f []float64) []uint8 {
	if len(f) == 0 {
		return nil
	}

	fMin := f[0]
	fMax := f[0]
	for _, val := range f {
		if val < fMin {
			fMin = val
		}
		if val > fMax {
			fMax = val
		}
	}

	result := make([]uint8, len(f))
	if fMax != fMin {
		scale := 255.0 / (fMax - fMin)
		for i, val := range f {
			normalized := (val - fMin) * scale
			if normalized < 0 {
				normalized = 0
			}
			if normalized > 255 {
				normalized = 255
			}
			result[i] = uint8(normalized)
		}
	} else {
		for i := range result {
			result[i] = 128
		}
	}

	return result
}

// vectorToImage converte vetor para imagem quadrada (ordem Fortran)
func vectorToImage(fNorm []uint8) (image.Image, error) {
	lado := int(math.Sqrt(float64(len(fNorm))))
	if lado*lado != len(fNorm) {
		return nil, fmt.Errorf("tamanho do vetor não é quadrado perfeito")
	}

	// Cria imagem em ordem Fortran (coluna por coluna)
	img := image.NewGray(image.Rect(0, 0, lado, lado))

	for col := 0; col < lado; col++ {
		for row := 0; row < lado; row++ {
			idx := col*lado + row // ordem Fortran
			if idx < len(fNorm) {
				img.Set(row, col, color.Gray{Y: fNorm[idx]})
			}
		}
	}

	return img, nil
}

// imageToPNGBytes converte imagem para bytes PNG
func imageToPNGBytes(img image.Image) ([]byte, error) {
	var buf bytes.Buffer
	err := png.Encode(&buf, img)
	if err != nil {
		return nil, err
	}
	return buf.Bytes(), nil
}

// loadHistory carrega histórico do teste.json
func loadHistory() ([]HistoryEntry, error) {
	mu.Lock()
	defer mu.Unlock()

	file, err := os.Open(testeJSONPath)
	if err != nil {
		return []HistoryEntry{}, nil // Retorna vazio se não existir
	}
	defer file.Close()

	var history []HistoryEntry
	decoder := json.NewDecoder(file)
	err = decoder.Decode(&history)
	if err != nil {
		return []HistoryEntry{}, nil
	}

	return history, nil
}

// estimateResources estima recursos necessários baseado no histórico
func estimateResources(model, signal string) (float64, float64, float64) {
	history, err := loadHistory()
	if err != nil || len(history) == 0 {
		return 0.01, 0.01, 0.1
	}

	// Encontra registros correspondentes
	var matching []HistoryEntry
	modelBase := filepath.Base(model)
	signalBase := filepath.Base(signal)

	for _, entry := range history {
		if filepath.Base(entry.Model) == modelBase &&
			strings.HasPrefix(filepath.Base(entry.Signal), signalBase) {
			matching = append(matching, entry)
		}
	}

	if len(matching) == 0 {
		return 0.01, 0.01, 0.1
	}

	// Usa o mais recente (assumindo que o último é o mais recente)
	reg := matching[len(matching)-1]

	// Calcula percentuais
	cpuCount, _ := cpu.Counts(true)
	cpuRequiredPct := reg.CPUUsed / float64(cpuCount)

	memInfo, _ := mem.VirtualMemory()
	memRequiredPct := (float64(reg.MemUsedBytes) / float64(memInfo.Total)) * 100.0

	return cpuRequiredPct, memRequiredPct, reg.Time
}

// getCurrentResources obtém uso atual de CPU e RAM
func getCurrentResources() (float64, float64, error) {
	cpuPercent, err := cpu.Percent(500*time.Millisecond, false)
	if err != nil {
		return 0, 0, err
	}

	memInfo, err := mem.VirtualMemory()
	if err != nil {
		return 0, 0, err
	}

	cpuUsage := 0.0
	if len(cpuPercent) > 0 {
		cpuUsage = cpuPercent[0]
	}

	return cpuUsage, memInfo.UsedPercent, nil
}

// processJob processa um job de reconstrução
func processJob(job JobRequest) error {
	payload := job.Payload
	conn := job.Conn

	startTime := time.Now()
	startDT := startTime.Format("2006-01-02 15:04:05")

	// Carrega modelo (pode vir como caminho relativo ../server/models/...)
	modelPath := payload.Model
	// Se for caminho relativo, resolve em relação ao diretório atual
	if !filepath.IsAbs(modelPath) {
		// Tenta resolver caminho relativo
		if absPath, err := filepath.Abs(modelPath); err == nil {
			modelPath = absPath
		}
	}
	H, err := loadCSVMatrix(modelPath)
	if err != nil {
		return fmt.Errorf("erro ao carregar modelo: %v", err)
	}

	// Carrega sinal (como no Python: os.path.join("..", signal + ".csv"))
	// signal vem como "client/signals/signal-30x30-0"
	signalPath := filepath.Join(rootDir, payload.Signal+".csv")
	g, err := loadCSVVector(signalPath)
	if err != nil {
		return fmt.Errorf("erro ao carregar sinal: %v", err)
	}

	// Aplica ganho
	gProcessed := applySignalGain(g)

	// Executa algoritmo
	var f []float64
	var iters int

	algorithm := strings.ToUpper(payload.Algorithm)
	if algorithm == "CGNR" {
		f, iters, _ = reconstructCGNR(H, gProcessed, MAX_ITERATIONS, TOL_REQUISITO)
	} else if algorithm == "CGNE" {
		f, iters, _ = reconstructCGNE(H, gProcessed, MAX_ITERATIONS, TOL_REQUISITO)
	} else {
		return fmt.Errorf("algoritmo desconhecido: %s", payload.Algorithm)
	}

	// Normaliza imagem
	fNorm := normalizeImage(f)

	// Converte para imagem
	img, err := vectorToImage(fNorm)
	if err != nil {
		return fmt.Errorf("erro ao criar imagem: %v", err)
	}

	// Converte para PNG
	imgBytes, err := imageToPNGBytes(img)
	if err != nil {
		return fmt.Errorf("erro ao codificar PNG: %v", err)
	}

	endTime := time.Now()
	endDT := endTime.Format("2006-01-02 15:04:05")
	processingTime := endTime.Sub(startTime).Seconds()

	// Codifica em base64
	imgB64 := base64.StdEncoding.EncodeToString(imgBytes)

	// Monta resposta
	header := ResponseHeader{
		Username:  payload.Username,
		Index:     payload.Idx,
		Algorithm: payload.Algorithm,
		Model:     payload.Model,
		Signal:    payload.Signal,
		StartDT:   startDT,
		EndDT:     endDT,
		Size:      fmt.Sprintf("%d", len(imgB64)),
		Iters:     iters,
		Time:      processingTime,
	}

	response := Response{
		Type: "2_",
		Payload: ResponseData{
			Header: header,
			Image:  imgB64,
		},
	}

	// Serializa e envia
	jsonData, err := json.Marshal(response)
	if err != nil {
		return fmt.Errorf("erro ao serializar JSON: %v", err)
	}

	mu.Lock()
	_, err = conn.Write(append(jsonData, '\n'))
	mu.Unlock()

	if err != nil {
		return fmt.Errorf("erro ao enviar resposta: %v", err)
	}

	log.Printf("[FINALIZADO] Process -> %s  idx -> %d", payload.Username, payload.Idx)
	return nil
}

// workerProcessItem processa itens da fila com controle de recursos
func workerProcessItem() {
	defer workerWg.Done()

	for job := range requestQueue {
		payload := job.Payload

		// Verifica recursos atuais
		cpuCurrent, memCurrent, err := getCurrentResources()
		if err != nil {
			log.Printf("[WORKER] Erro ao obter recursos: %v", err)
			continue
		}

		// Estima recursos necessários
		cpuRequired, memRequired, timeEstimate := estimateResources(payload.Model, payload.Signal)

		log.Printf("[WORKER] CPU_atual=%.1f%% | RAM_atual=%.1f%% | Nec -> CPU=%.1f%% RAM=%.1f%% | Lim -> CPU=%.1f%% RAM=%.1f%%",
			cpuCurrent, memCurrent, cpuRequired, memRequired, CPU_LIMIT, MEM_LIMIT)

		// Verifica se há recursos suficientes
		if (cpuCurrent+cpuRequired > CPU_LIMIT) || (memCurrent+memRequired > MEM_LIMIT) {
			log.Printf("[WORKER] Recursos insuficientes — Requeue -> %s idx=%d", payload.Username, payload.Idx)

			// Reenfileira após um delay
			time.Sleep(time.Duration(math.Min(timeEstimate, 1.0)) * time.Second)
			select {
			case requestQueue <- job:
			default:
				log.Printf("[WORKER] Fila cheia, descartando job")
			}
			continue
		}

		// Processa job
		log.Printf("[WORKER] Processando -> %s idx=%d", payload.Username, payload.Idx)
		if err := processJob(job); err != nil {
			log.Printf("[WORKER] Erro ao processar job: %v", err)
		}
	}
}

// handleClient gerencia conexão de um cliente
func handleClient(conn net.Conn) {
	defer conn.Close()

	addr := conn.RemoteAddr()
	log.Printf("[NOVA CONEXÃO] %s conectado", addr)

	// Buffer para ler dados (similar ao servidor Python que usa recv(1000000))
	buffer := make([]byte, 1000000)

	for {
		// Lê dados do socket (bloqueia até receber dados)
		n, err := conn.Read(buffer)
		if err != nil {
			if err.Error() != "EOF" {
				log.Printf("[ERRO] Erro ao ler do cliente: %v", err)
			}
			break
		}

		if n == 0 {
			break
		}

		data := string(buffer[:n])

		// Verifica comando EXIT
		if strings.HasPrefix(data, "EXIT") {
			log.Printf("[DESCONECTADO] %s encerrou a conexão", addr)
			break
		}

		// Processa mensagem tipo 2_
		if strings.HasPrefix(data, "2_") {
			// Encontra o início do JSON (após o segundo |)
			firstPipe := strings.Index(data, "|")
			if firstPipe == -1 {
				log.Printf("[ERRO] Primeiro pipe não encontrado")
				continue
			}

			secondPipe := strings.Index(data[firstPipe+1:], "|")
			if secondPipe == -1 {
				log.Printf("[ERRO] Segundo pipe não encontrado")
				continue
			}

			// Ajusta o índice do segundo pipe
			secondPipe = firstPipe + 1 + secondPipe

			jsonStr := data[secondPipe+1:]

			// Remove espaços e quebras de linha do início e fim do JSON
			jsonStr = strings.TrimSpace(jsonStr)

			var payload Payload
			if err := json.Unmarshal([]byte(jsonStr), &payload); err != nil {
				log.Printf("[ERRO] Erro ao decodificar JSON: %v", err)
				continue
			}

			// Adiciona à fila
			job := JobRequest{
				Payload: payload,
				Conn:    conn,
			}

			select {
			case requestQueue <- job:
				log.Printf("[SUPERVISOR] Job enviado para fila -> %s idx=%d", payload.Username, payload.Idx)
			default:
				log.Printf("[ERRO] Fila cheia, descartando job")
			}
		}
	}
}

// min retorna o menor valor entre dois inteiros
func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func main() {
	// Inicia profiler worker (monitora CPU/RAM e escreve no CSV)
	go profilerWorker()
	log.Printf("[INFO] Profiler de performance iniciado")

	// Inicia workers
	for i := 0; i < MAX_WORKERS; i++ {
		workerWg.Add(1)
		go workerProcessItem()
	}

	// Inicia servidor
	listener, err := net.Listen("tcp", ":"+PORT)
	if err != nil {
		log.Fatalf("Erro ao iniciar servidor: %v", err)
	}
	defer listener.Close()

	// Cleanup ao encerrar
	defer func() {
		closeProfiler <- true
		if performanceCSV != nil {
			performanceCSV.Close()
		}
	}()

	log.Printf("Servidor iniciado e aguardando conexões na porta %s...", PORT)
	log.Printf("[INFO] Limites configurados: CPU=%.1f%% | RAM=%.1f%%", CPU_LIMIT, MEM_LIMIT)

	// Aceita conexões
	for {
		conn, err := listener.Accept()
		if err != nil {
			log.Printf("Erro ao aceitar conexão: %v", err)
			continue
		}

		go handleClient(conn)
	}
}
