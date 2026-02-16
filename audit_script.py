import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import sys

# ==========================================
# CONFIGURATION
# ==========================================
# Make sure this matches your CSV filename exactly
FILE_NAME = 'TRADE_HISTORY_CSV_1103885929_2025-08-01_2026-02-16_0_.csv'

def generate_audit():
    # Auto-detect file path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, FILE_NAME)

    try:
        # ---------------------------------------------------------
        # 1. LOAD & PROCESS DATA
        # ---------------------------------------------------------
        print(f"Loading data from: {FILE_NAME}...")
        
        # Check if file exists
        if not os.path.exists(file_path):
            print(f"ERROR: File not found at {file_path}")
            return

        df = pd.read_csv(file_path)
        df.columns = df.columns.str.strip()
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Logic: Sell = Inflow (+), Buy = Outflow (-)
        df['Cashflow'] = df.apply(lambda row: row['Trade Value'] if row['Buy/Sell'].strip().upper() == 'SELL' else -row['Trade Value'], axis=1)

        # Detect Segments
        if 'Segment' in df.columns:
            unique_segments = list(df['Segment'].unique())
            segment_str = ", ".join(unique_segments)
        else:
            segment_str = "Equity & F&O (Options) [Derived]"

        # ---------------------------------------------------------
        # 2. CALCULATE METRICS
        # ---------------------------------------------------------
        # Daily Stats
        daily_pnl = df.groupby('Date')['Cashflow'].sum().reset_index()
        daily_pnl['Cumulative P&L'] = daily_pnl['Cashflow'].cumsum()
        daily_pnl['Running Peak'] = daily_pnl['Cumulative P&L'].cummax()
        daily_pnl['Drawdown'] = daily_pnl['Cumulative P&L'] - daily_pnl['Running Peak']
        
        # Scalar Metrics
        total_trades = len(df)
        net_profit = df['Cashflow'].sum()
        
        winning_days = daily_pnl[daily_pnl['Cashflow'] > 0]
        losing_days = daily_pnl[daily_pnl['Cashflow'] < 0]
        
        win_rate = (len(winning_days) / len(daily_pnl)) * 100
        avg_win = winning_days['Cashflow'].mean() if not winning_days.empty else 0
        avg_loss = abs(losing_days['Cashflow'].mean()) if not losing_days.empty else 0
        
        # Safe Profit Factor
        gross_loss = abs(losing_days['Cashflow'].sum())
        profit_factor = winning_days['Cashflow'].sum() / gross_loss if gross_loss != 0 else 0
        
        max_dd = daily_pnl['Drawdown'].min()
        risk_reward = avg_win / avg_loss if avg_loss != 0 else 0

        # ---------------------------------------------------------
        # 3. GENERATE TEXT REPORT (performance_metrics.txt)
        # ---------------------------------------------------------
        # We use the Rupee symbol here because we are saving with utf-8 encoding
        report_text = f"""
==================================================================
 FY25-26 TRADING PERFORMANCE AUDIT REPORT
==================================================================
Audit Date:       {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
Data Source:      {FILE_NAME}
Total Executions: {total_trades}
Segments:         {segment_str}

------------------------------------------------------------------
 KEY PERFORMANCE METRICS
------------------------------------------------------------------
Net Profit (Realized):  ₹{net_profit:,.2f}
Profit Factor:          {profit_factor:.2f}
Daily Win Rate:         {win_rate:.1f}%
Risk/Reward Ratio:      1 : {risk_reward:.2f}
Max Drawdown:           ₹{max_dd:,.0f}

------------------------------------------------------------------
 AVERAGE TRADE STATISTICS
------------------------------------------------------------------
Avg Daily Win:          ₹{avg_win:,.2f}
Avg Daily Loss:         ₹{avg_loss:,.2f}

==================================================================
*Generated via Python Audit Script using Pandas Analysis*
==================================================================
"""
        # Save Text Report (Safe Encoding)
        txt_path = os.path.join(script_dir, 'performance_metrics.txt')
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(report_text)
        print(f"-> SUCCESS: Metrics saved to 'performance_metrics.txt'")

        # ---------------------------------------------------------
        # 4. PRINT SUMMARY TO CONSOLE (Safe for Windows)
        # ---------------------------------------------------------
        # We use 'INR' here to avoid 'charmap' errors in the console
        print("-" * 50)
        print(" FY25-26 TRADING PERFORMANCE AUDIT")
        print("-" * 50)
        print(f" Data Source:     {FILE_NAME}")
        print(f" Segments:        {segment_str}")
        print(f" Total Trades:    {total_trades}")
        print("-" * 50)
        print(f" Net Profit:      INR {net_profit:,.2f}")
        print(f" Profit Factor:   {profit_factor:.2f}")
        print(f" Daily Win Rate:  {win_rate:.1f}%")
        print(f" Avg Win:         INR {avg_win:,.0f}")
        print(f" Avg Loss:        INR {avg_loss:,.0f}")
        print(f" Risk/Reward:     1 : {risk_reward:.2f}")
        print(f" Max Drawdown:    INR {max_dd:,.0f}")
        print("-" * 50)

        # ---------------------------------------------------------
        # 5. GENERATE DASHBOARD IMAGE
        # ---------------------------------------------------------
        # Hourly Data Prep
        df['Time'] = pd.to_datetime(df['Time'], format='%H:%M:%S').dt.time
        df['Hour'] = df['Time'].apply(lambda x: x.hour)
        hourly_pnl = df.groupby('Hour')['Cashflow'].sum().reset_index()
        hourly_colors = ['#00C853' if x > 0 else '#FF5252' for x in hourly_pnl['Cashflow']]

        fig = plt.figure(figsize=(16, 12))
        grid = plt.GridSpec(2, 2, height_ratios=[1, 0.8], hspace=0.3, wspace=0.2)

        # Chart 1: Equity Curve
        ax1 = fig.add_subplot(grid[0, :])
        ax1.plot(daily_pnl['Date'], daily_pnl['Cumulative P&L'], color='#00C853', linewidth=2)
        ax1.fill_between(daily_pnl['Date'], daily_pnl['Cumulative P&L'], color='#00C853', alpha=0.1)
        ax1.set_title('Account Growth (Equity Curve)', fontsize=14, fontweight='bold')
        ax1.grid(True, linestyle='--', alpha=0.3)
        ax1.set_ylabel('Net Profit')

        # Chart 2: Drawdown
        ax2 = fig.add_subplot(grid[1, 0])
        ax2.plot(daily_pnl['Date'], daily_pnl['Drawdown'], color='#FF5252', linewidth=1)
        ax2.fill_between(daily_pnl['Date'], daily_pnl['Drawdown'], color='#FF5252', alpha=0.1)
        ax2.set_title('Risk Profile: Drawdown', fontsize=12, fontweight='bold')
        ax2.grid(True, linestyle='--', alpha=0.3)
        ax2.set_ylabel('Drawdown')

        # Chart 3: Hourly Efficiency
        ax3 = fig.add_subplot(grid[1, 1])
        sns.barplot(x='Hour', y='Cashflow', data=hourly_pnl, palette=hourly_colors, ax=ax3)
        ax3.set_title('Time-of-Day Efficiency', fontsize=12, fontweight='bold')
        ax3.axhline(0, color='black', linewidth=0.8)
        ax3.set_ylabel('Net P&L')

        fig.suptitle('FY25-26 Discretionary Trading Performance Audit', fontsize=20, fontweight='bold', y=0.95)
        
        img_path = os.path.join(script_dir, 'trading_performance_dashboard.png')
        plt.savefig(img_path, dpi=300)
        print(f"-> SUCCESS: Dashboard saved to 'trading_performance_dashboard.png'")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error: {e}")

if __name__ == "__main__":
    generate_audit()
