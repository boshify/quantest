document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Fetch available symbols
    fetchSymbols();
    
    // Setup range input listeners
    setupRangeInputs();
    
    // Setup form submission
    const form = document.getElementById('backtestForm');
    form.addEventListener('submit', handleFormSubmit);
    
    // Setup symbol and timeframe change listeners
    document.getElementById('symbol').addEventListener('change', updateMaxCandles);
    document.getElementById('timeframe').addEventListener('change', updateMaxCandles);
});

async function fetchSymbols() {
    try {
        const response = await fetch('/api/symbols');
        const symbols = await response.json();
        
        const symbolSelect = document.getElementById('symbol');
        symbolSelect.innerHTML = '';
        
        symbols.forEach(symbol => {
            const option = document.createElement('option');
            option.value = symbol;
            option.textContent = symbol;
            symbolSelect.appendChild(option);
        });
        
        // After loading symbols, fetch parameter descriptions
        fetchParameterDescriptions();
        
        // Update max candles for the selected symbol
        updateMaxCandles();
    } catch (error) {
        console.error('Error fetching symbols:', error);
    }
}

async function fetchParameterDescriptions() {
    try {
        const response = await fetch('/api/param-descriptions');
        const descriptions = await response.json();
        
        // Update tooltips with descriptions
        Object.entries(descriptions).forEach(([param, description]) => {
            const tooltip = document.querySelector(`label[for="${param}"] i`);
            if (tooltip) {
                tooltip.setAttribute('data-bs-toggle', 'tooltip');
                tooltip.setAttribute('data-bs-placement', 'right');
                tooltip.setAttribute('title', description);
                new bootstrap.Tooltip(tooltip);
            }
        });
    } catch (error) {
        console.error('Error fetching parameter descriptions:', error);
    }
}

async function updateMaxCandles() {
    const symbol = document.getElementById('symbol').value;
    const timeframe = document.getElementById('timeframe').value;
    
    try {
        const response = await fetch(`/api/max-candles/${symbol}/${timeframe}`);
        const data = await response.json();
        
        const limitInput = document.getElementById('limit');
        limitInput.max = data.max_candles;
        
        // If current value is higher than max, adjust it
        if (parseInt(limitInput.value) > data.max_candles) {
            limitInput.value = data.max_candles;
            document.getElementById('limitValue').textContent = data.max_candles;
        }
    } catch (error) {
        console.error('Error fetching max candles:', error);
    }
}

function setupRangeInputs() {
    // Setup limit range input
    const limitInput = document.getElementById('limit');
    const limitValue = document.getElementById('limitValue');
    limitInput.addEventListener('input', function() {
        limitValue.textContent = this.value;
    });
    
    // Setup liquidity threshold range input
    const liquidityInput = document.getElementById('liquidity_threshold');
    const liquidityValue = document.getElementById('liquidityThresholdValue');
    liquidityInput.addEventListener('input', function() {
        liquidityValue.textContent = this.value;
    });
    
    // Setup MSS threshold range input
    const mssInput = document.getElementById('mss_threshold');
    const mssValue = document.getElementById('mssThresholdValue');
    mssInput.addEventListener('input', function() {
        mssValue.textContent = this.value;
    });
}

async function handleFormSubmit(e) {
    e.preventDefault();
    
    // Show loading state
    const submitButton = e.target.querySelector('button[type="submit"]');
    const originalText = submitButton.textContent;
    submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Running Backtest...';
    submitButton.disabled = true;
    
    // Collect form data
    const params = {
        symbol: document.getElementById('symbol').value,
        timeframe: document.getElementById('timeframe').value,
        limit: parseInt(document.getElementById('limit').value),
        strategy_params: {
            swing_period: parseInt(document.getElementById('swing_period').value),
            external_liquidity_period: parseInt(document.getElementById('external_liquidity_period').value),
            liquidity_threshold: parseFloat(document.getElementById('liquidity_threshold').value),
            sweep_period: parseInt(document.getElementById('sweep_period').value),
            mss_threshold: parseFloat(document.getElementById('mss_threshold').value),
            tp_period: parseInt(document.getElementById('tp_period').value)
        }
    };

    try {
        // Run backtest
        const response = await fetch('/backtest', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(params)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const results = await response.json();
        
        // Update metrics
        updateMetrics(results);
        
        // Update equity curve
        updateEquityCurve(results.trades);
        
    } catch (error) {
        console.error('Error running backtest:', error);
        alert('Error running backtest. Please check the console for details.');
    } finally {
        // Reset button state
        submitButton.innerHTML = originalText;
        submitButton.disabled = false;
    }
}

function updateMetrics(results) {
    const metricsDiv = document.getElementById('metrics');
    const tradeStatsDiv = document.getElementById('tradeStats');
    
    // Clear previous results
    metricsDiv.innerHTML = '';
    tradeStatsDiv.innerHTML = '';
    
    // Performance Metrics
    const metrics = [
        { label: 'Total Trades', value: results.total_trades },
        { label: 'Win Rate', value: `${results.win_rate}%` },
        { label: 'Average R', value: results.avg_r.toFixed(2) },
        { label: 'Profit Factor', value: results.profit_factor.toFixed(2) },
        { label: 'Net PnL', value: results.net_pnl.toFixed(2), isPnL: true }
    ];
    
    metrics.forEach(metric => {
        const div = document.createElement('div');
        div.className = 'metric-item';
        div.innerHTML = `
            <span class="metric-label">${metric.label}</span>
            <span class="metric-value ${metric.isPnL ? (metric.value >= 0 ? 'positive' : 'negative') : ''}">${metric.value}</span>
        `;
        metricsDiv.appendChild(div);
    });
    
    // Trade Statistics
    if (results.trades && results.trades.length > 0) {
        const trades = results.trades;
        const winningTrades = trades.filter(t => t.pnl > 0);
        const losingTrades = trades.filter(t => t.pnl < 0);
        
        const stats = [
            { label: 'Winning Trades', value: winningTrades.length },
            { label: 'Losing Trades', value: losingTrades.length },
            { label: 'Average Win', value: (winningTrades.reduce((sum, t) => sum + t.pnl, 0) / winningTrades.length || 0).toFixed(2) },
            { label: 'Average Loss', value: (losingTrades.reduce((sum, t) => sum + t.pnl, 0) / losingTrades.length || 0).toFixed(2) },
            { label: 'Largest Win', value: Math.max(...trades.map(t => t.pnl)).toFixed(2) },
            { label: 'Largest Loss', value: Math.min(...trades.map(t => t.pnl)).toFixed(2) }
        ];
        
        stats.forEach(stat => {
            const div = document.createElement('div');
            div.className = 'metric-item';
            div.innerHTML = `
                <span class="metric-label">${stat.label}</span>
                <span class="metric-value">${stat.value}</span>
            `;
            tradeStatsDiv.appendChild(div);
        });
    }
}

function updateEquityCurve(trades) {
    if (!trades || trades.length === 0) {
        document.getElementById('equityCurve').innerHTML = 'No trades to display';
        return;
    }
    
    // Calculate cumulative PnL
    let cumulativePnL = 0;
    const equityData = trades.map(trade => {
        cumulativePnL += trade.pnl;
        return {
            time: new Date(trade.exit_time),
            pnl: cumulativePnL
        };
    });
    
    const trace = {
        x: equityData.map(d => d.time),
        y: equityData.map(d => d.pnl),
        type: 'scatter',
        mode: 'lines',
        name: 'Equity Curve',
        line: {
            color: '#3498db',
            width: 2
        }
    };
    
    const layout = {
        title: {
            text: 'Equity Curve',
            font: {
                size: 20,
                color: '#2c3e50'
            }
        },
        xaxis: {
            title: 'Time',
            gridcolor: '#ecf0f1',
            zerolinecolor: '#ecf0f1'
        },
        yaxis: {
            title: 'Cumulative PnL',
            gridcolor: '#ecf0f1',
            zerolinecolor: '#ecf0f1'
        },
        template: 'plotly_white',
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        margin: {
            l: 50,
            r: 50,
            t: 50,
            b: 50
        }
    };
    
    Plotly.newPlot('equityCurve', [trace], layout);
} 