document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('backtestForm');
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
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

            const results = await response.json();
            
            // Update metrics
            updateMetrics(results);
            
            // Update equity curve
            updateEquityCurve(results.trades);
            
        } catch (error) {
            console.error('Error running backtest:', error);
            alert('Error running backtest. Please check the console for details.');
        }
    });
});

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
        name: 'Equity Curve'
    };
    
    const layout = {
        title: 'Equity Curve',
        xaxis: {
            title: 'Time'
        },
        yaxis: {
            title: 'Cumulative PnL'
        },
        template: 'plotly_white'
    };
    
    Plotly.newPlot('equityCurve', [trace], layout);
} 