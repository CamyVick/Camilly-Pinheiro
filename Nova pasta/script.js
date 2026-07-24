// ============================================
// 1. CONFIGURAÇÃO INICIAL
// ============================================
const UPDATE_INTERVAL = 3000; // 3 segundos
let salesChart, regionChart;

// ============================================
// 2. GERADOR DE DADOS ALEATÓRIOS (Simula API)
// ============================================
function generateRandomData() {
    const categories = ['Eletrônicos', 'Roupas', 'Livros', 'Casa', 'Esportes'];
    const regions = ['Norte', 'Nordeste', 'Centro-Oeste', 'Sudeste', 'Sul'];
    const statuses = ['Concluído', 'Pendente', 'Cancelado'];
    const products = ['Smartphone', 'Notebook', 'Camisa', 'Livro JS', 'Sofá', 'Tênis'];
    const clients = ['Ana Silva', 'Carlos Souza', 'Mariana Lima', 'João Pedro', 'Lucas Santos'];

    // Vendas por categoria
    const salesByCategory = {};
    categories.forEach(cat => {
        salesByCategory[cat] = Math.floor(Math.random() * 10000) + 1000;
    });

    // Visitantes por região
    const visitorsByRegion = {};
    regions.forEach(reg => {
        visitorsByRegion[reg] = Math.floor(Math.random() * 800) + 200;
    });

    // Últimas transações
    const transactions = [];
    for (let i = 0; i < 7; i++) {
        transactions.push({
            cliente: clients[Math.floor(Math.random() * clients.length)],
            produto: products[Math.floor(Math.random() * products.length)],
            valor: (Math.random() * 500 + 50).toFixed(2),
            status: statuses[Math.floor(Math.random() * statuses.length)]
        });
    }

    // KPIs
    const totalSales = Object.values(salesByCategory).reduce((a, b) => a + b, 0);
    const totalVisitors = Object.values(visitorsByRegion).reduce((a, b) => a + b, 0);
    const conversion = ((Math.random() * 8) + 2).toFixed(1);
    const satisfaction = ((Math.random() * 15) + 80).toFixed(1);

    // Tendências (variação aleatória)
    const trends = {
        sales: (Math.random() * 10 - 3).toFixed(1),
        visitors: (Math.random() * 12 - 4).toFixed(1),
        conversion: (Math.random() * 4 - 1.5).toFixed(1),
        satisfaction: (Math.random() * 3 - 0.5).toFixed(1)
    };

    return {
        salesByCategory,
        visitorsByRegion,
        transactions,
        kpis: { totalSales, totalVisitors, conversion, satisfaction },
        trends
    };
}

// ============================================
// 3. ATUALIZAR KPIs
// ============================================
function updateKPIs(data) {
    // Formata valores
    document.getElementById('totalSales').textContent = 
        `R$ ${data.kpis.totalSales.toLocaleString('pt-BR')}`;
    
    document.getElementById('totalVisitors').textContent = 
        data.kpis.totalVisitors.toLocaleString('pt-BR');
    
    document.getElementById('conversionRate').textContent = 
        `${data.kpis.conversion}%`;
    
    document.getElementById('satisfaction').textContent = 
        `${data.kpis.satisfaction}%`;

    // Tendências (com setas e cores)
    updateTrend('salesTrend', data.trends.sales, 'R$');
    updateTrend('visitorsTrend', data.trends.visitors, '');
    updateTrend('conversionTrend', data.trends.conversion, '');
    updateTrend('satisfactionTrend', data.trends.satisfaction, '');
}

function updateTrend(elementId, value, prefix) {
    const el = document.getElementById(elementId);
    const num = parseFloat(value);
    const symbol = num >= 0 ? '▲' : '▼';
    const color = num >= 0 ? 'up' : 'down';
    el.className = `trend ${color}`;
    el.textContent = `${symbol} ${Math.abs(num)}%`;
}

// ============================================
// 4. ATUALIZAR TABELA
// ============================================
function updateTable(transactions) {
    const tbody = document.getElementById('tableBody');
    tbody.innerHTML = '';
    
    transactions.forEach(trans => {
        const tr = document.createElement('tr');
        const statusClass = {
            'Concluído': 'success',
            'Pendente': 'warning',
            'Cancelado': 'danger'
        }[trans.status] || 'warning';

        tr.innerHTML = `
            <td>${trans.cliente}</td>
            <td>${trans.produto}</td>
            <td>R$ ${parseFloat(trans.valor).toFixed(2)}</td>
            <td><span class="status-badge ${statusClass}">${trans.status}</span></td>
        `;
        tbody.appendChild(tr);
    });
}

// ============================================
// 5. GRÁFICOS (Chart.js)
// ============================================
function initCharts() {
    const ctx1 = document.getElementById('salesChart').getContext('2d');
    const ctx2 = document.getElementById('regionChart').getContext('2d');

    // Gráfico de Vendas (Barras)
    salesChart = new Chart(ctx1, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Vendas (R$)',
                data: [],
                backgroundColor: 'rgba(0, 212, 255, 0.6)',
                borderColor: '#00d4ff',
                borderWidth: 2,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    ticks: { color: '#8899aa' },
                    grid: { color: '#1a2332' }
                },
                x: {
                    ticks: { color: '#8899aa' },
                    grid: { color: '#1a2332' }
                }
            }
        }
    });

    // Gráfico de Visitantes (Donut)
    regionChart = new Chart(ctx2, {
        type: 'doughnut',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [
                    '#00d4ff', '#7b2ffc', '#ff6b6b', '#ffd93d', '#6bcb77'
                ],
                borderColor: '#111b2a',
                borderWidth: 3
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    labels: { color: '#e0e6ed', padding: 15 }
                }
            }
        }
    });
}

function updateCharts(data) {
    // Atualiza gráfico de vendas
    const categories = Object.keys(data.salesByCategory);
    const values = Object.values(data.salesByCategory);
    
    salesChart.data.labels = categories;
    salesChart.data.datasets[0].data = values;
    salesChart.update();

    // Atualiza gráfico de regiões
    const regions = Object.keys(data.visitorsByRegion);
    const visitors = Object.values(data.visitorsByRegion);
    
    regionChart.data.labels = regions;
    regionChart.data.datasets[0].data = visitors;
    regionChart.update();
}

// ============================================
// 6. TIMESTAMP DE ATUALIZAÇÃO
// ============================================
function updateTimestamp() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('pt-BR');
    document.getElementById('lastUpdate').textContent = `Atualizado: ${timeStr}`;
}

// ============================================
// 7. LOOP PRINCIPAL
// ============================================
function refreshDashboard() {
    const data = generateRandomData();
    
    updateKPIs(data);
    updateTable(data.transactions);
    updateCharts(data);
    updateTimestamp();
}

// ============================================
// 8. INICIALIZAÇÃO
// ============================================
initCharts();
refreshDashboard(); // Primeira carga

// Atualiza a cada X segundos
setInterval(refreshDashboard, UPDATE_INTERVAL);

console.log('📊 Dashboard BI em tempo real iniciado!');
console.log('⏱️ Atualizando a cada', UPDATE_INTERVAL / 1000, 'segundos');