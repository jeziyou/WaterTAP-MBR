"""
WaterTAP MBR 工艺设计工具 - Streamlit 版本（Python 3.14 兼容版）
=================================================================
使用纯 Pyomo 实现 MBR 模拟，避免 IDAES 元类冲突
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json

# ============================================================
# 纯 Pyomo MBR 模拟（不依赖 IDAES，避免元类冲突）
# ============================================================
def run_mbr_simulation_pure(flow_rate, tss_conc, toc_conc, nonvolatile_toc_conc,
                            water_recovery, tss_removal, toc_removal, nonvolatile_toc_removal):
    """
    使用纯 Python 计算 MBR 模拟结果
    基于 WaterTAP MBR 零阶模型的简化算法
    """
    try:
        # 进水流量 (kg/hr，水密度按 1000 kg/m³)
        Q_in = flow_rate  # m³/hr = 1000 kg/hr (近似)
        
        # 计算进水质量流量 (kg/hr)
        inlet_tss_mass = (tss_conc / 1e6) * Q_in
        inlet_toc_mass = (toc_conc / 1e6) * Q_in
        inlet_nv_toc_mass = (nonvolatile_toc_conc / 1e6) * Q_in
        
        # 计算产水流量
        Q_outlet = Q_in * water_recovery
        Q_byproduct = Q_in - Q_outlet
        
        # 计算产水组分（基于去除率）
        outlet_tss_mass = inlet_tss_mass * (1 - tss_removal)
        outlet_toc_mass = inlet_toc_mass * (1 - toc_removal)
        outlet_nv_toc_mass = inlet_nv_toc_mass * (1 - nonvolatile_toc_removal)
        
        # 计算产水浓度
        outlet_tss_conc = (outlet_tss_mass / Q_outlet) * 1e6 if Q_outlet > 0 else 0
        outlet_toc_conc = (outlet_toc_mass / Q_outlet) * 1e6 if Q_outlet > 0 else 0
        outlet_nv_toc_conc = (outlet_nv_toc_mass / Q_outlet) * 1e6 if Q_outlet > 0 else 0
        
        # 能耗估算（基于 WaterTAP MBR 零阶模型）
        # 典型 MBR 能耗: 0.5-2.0 kWh/m³
        electricity_intensity = 0.814  # kWh/m³ (基于典型值)
        power_consumption_kw = electricity_intensity * Q_in
        
        return {
            "success": True,
            "performance": {
                "water_recovery": water_recovery,
                "tss_removal": tss_removal,
                "toc_removal": toc_removal,
                "nonvolatile_toc_removal": nonvolatile_toc_removal,
                "power_consumption_kw": power_consumption_kw,
                "electricity_intensity": electricity_intensity,
            },
            "inlet": {
                "flow_rate": Q_in,
                "tss_conc": tss_conc,
                "toc_conc": toc_conc,
                "nonvolatile_toc_conc": nonvolatile_toc_conc,
                "tss_mass": inlet_tss_mass,
                "toc_mass": inlet_toc_mass,
                "nonvolatile_toc_mass": inlet_nv_toc_mass,
            },
            "outlet": {
                "flow_rate": Q_outlet,
                "tss_conc": outlet_tss_conc,
                "toc_conc": outlet_toc_conc,
                "nonvolatile_toc_conc": outlet_nv_toc_conc,
                "tss_mass": outlet_tss_mass,
                "toc_mass": outlet_toc_mass,
                "nonvolatile_toc_mass": outlet_nv_toc_mass,
            },
            "byproduct": {
                "flow_rate": Q_byproduct,
            }
        }
        
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


# ============================================================
# Streamlit 页面配置
# ============================================================
st.set_page_config(
    page_title="WaterTAP MBR 设计工具",
    page_icon="🚰",
    layout="wide"
)


def main():
    st.title("🚰 WaterTAP MBR 工艺设计工具")
    st.markdown("基于 **MBR 零阶模型** 的膜生物反应器模拟与设计")
    st.caption("✅ Python 3.14 兼容模式 - 纯计算实现")
    
    # 侧边栏 - 参数设置
    st.sidebar.header("⚙️ 参数设置")
    
    st.sidebar.subheader("📥 进水水质参数")
    flow_rate = st.sidebar.number_input("进水流量 (m³/hr)", min_value=1, max_value=10000, value=1000, step=100)
    tss_conc = st.sidebar.number_input("TSS 浓度 (mg/L)", min_value=0, max_value=1000, value=200, step=10)
    toc_conc = st.sidebar.number_input("TOC 浓度 (mg/L)", min_value=0, max_value=1000, value=150, step=10)
    nonvolatile_toc_conc = st.sidebar.number_input("非挥发性 TOC 浓度 (mg/L)", min_value=0, max_value=1000, value=100, step=10)
    
    st.sidebar.subheader("🔧 工艺运行参数")
    water_recovery = st.sidebar.slider("水回收率", min_value=0.0, max_value=1.0, value=0.9999, step=0.0001)
    tss_removal = st.sidebar.slider("TSS 去除率", min_value=0.0, max_value=1.0, value=0.5, step=0.01)
    toc_removal = st.sidebar.slider("TOC 去除率", min_value=0.0, max_value=1.0, value=0.70854, step=0.01)
    nonvolatile_toc_removal = st.sidebar.slider("非挥发性 TOC 去除率", min_value=0.0, max_value=1.0, value=0.6, step=0.01)
    
    # 运行按钮
    if st.sidebar.button("▶️ 运行模拟", type="primary", use_container_width=True):
        with st.spinner("正在运行模拟..."):
            results = run_mbr_simulation_pure(
                flow_rate, tss_conc, toc_conc, nonvolatile_toc_conc,
                water_recovery, tss_removal, toc_removal, nonvolatile_toc_removal
            )
        
        if results.get("success"):
            st.session_state['results'] = results
            st.success("✅ 模拟成功完成！")
        else:
            st.error(f"❌ 模拟失败: {results.get('error')}")
            if results.get("traceback"):
                with st.expander("查看详细错误信息"):
                    st.code(results["traceback"])
            st.session_state['results'] = None
    
    # 显示结果
    results = st.session_state.get('results')
    
    if results and results.get("success"):
        display_results(results)
    elif results is None:
        st.info("👈 请在左侧设置参数，然后点击 **运行模拟** 按钮")
        
        # 显示说明
        with st.expander("📖 关于此工具"):
            st.markdown("""
            ### 功能说明
            本工具基于 **MBR（膜生物反应器）零阶模型** 进行工艺模拟：
            
            - **进水参数**: 流量、TSS、TOC 浓度
            - **工艺参数**: 水回收率、各组分去除率
            - **输出结果**: 产水流量、出水浓度、能耗估算
            
            ### 计算原理
            采用质量平衡方程：
            - 产水流量 = 进水流量 × 水回收率
            - 出水浓度 = 进水浓度 × (1 - 去除率)
            - 能耗基于典型 MBR 运行参数估算
            
            ### 注意
            此为简化计算版本，如需完整 WaterTAP 模拟，请使用 Python 3.10-3.12 环境。
            """)
    
    # 页脚
    st.markdown("---")
    st.caption("基于 MBR 零阶模型 | Python 3.14 兼容版本")


def display_results(results):
    """显示模拟结果"""
    perf = results['performance']
    inlet = results['inlet']
    outlet = results['outlet']
    byproduct = results['byproduct']
    
    # 性能指标
    st.subheader("📊 性能指标")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("水回收率", f"{perf['water_recovery']*100:.2f}%")
    col2.metric("TSS 去除率", f"{perf['tss_removal']*100:.1f}%")
    col3.metric("TOC 去除率", f"{perf['toc_removal']*100:.1f}%")
    col4.metric("功率消耗", f"{perf['power_consumption_kw']:.2f} kW")
    
    # 工艺流程图
    st.subheader("🔄 MBR 工艺流程")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[1], y=[2], mode='markers+text', 
                              marker=dict(size=80, color='#4CAF50'), 
                              text=['进水'], textposition='middle center', 
                              textfont=dict(color='white', size=13)))
    fig.add_trace(go.Scatter(x=[2.5], y=[2], mode='markers+text', 
                              marker=dict(size=120, color='#2196F3'), 
                              text=['MBR'], textposition='middle center', 
                              textfont=dict(color='white', size=15)))
    fig.add_trace(go.Scatter(x=[4], y=[2.5], mode='markers+text', 
                              marker=dict(size=70, color='#8BC34A'), 
                              text=['产水'], textposition='middle center', 
                              textfont=dict(color='white', size=11)))
    fig.add_trace(go.Scatter(x=[4], y=[1.5], mode='markers+text', 
                              marker=dict(size=50, color='#FF9800'), 
                              text=['浓水'], textposition='middle center', 
                              textfont=dict(color='white', size=11)))
    
    # 箭头
    fig.add_annotation(x=1.5, y=2, ax=2, ay=2, showarrow=True, arrowhead=2, 
                       arrowsize=1.5, arrowwidth=2, arrowcolor='#333')
    fig.add_annotation(x=3, y=2.3, ax=3.5, ay=2.45, showarrow=True, arrowhead=2, 
                       arrowsize=1.5, arrowwidth=2, arrowcolor='#333')
    fig.add_annotation(x=3, y=1.7, ax=3.5, ay=1.55, showarrow=True, arrowhead=2, 
                       arrowsize=1.5, arrowwidth=2, arrowcolor='#333')
    
    # 数据标签
    fig.add_annotation(x=1, y=1.5, text=f"Q={inlet['flow_rate']:.0f} m³/h", 
                       showarrow=False, font=dict(size=11, color='#666'))
    fig.add_annotation(x=2.5, y=1.2, text=f"P={perf['power_consumption_kw']:.1f} kW", 
                       showarrow=False, font=dict(size=11, color='#666'))
    fig.add_annotation(x=4, y=3, text=f"Q={outlet['flow_rate']:.1f} m³/h", 
                       showarrow=False, font=dict(size=11, color='#666'))
    fig.add_annotation(x=4, y=1, text=f"Q={byproduct['flow_rate']:.2f} m³/h", 
                       showarrow=False, font=dict(size=11, color='#666'))
    
    fig.update_layout(height=300, showlegend=False, 
                      xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0.5, 4.5]),
                      yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0.5, 3.5]),
                      plot_bgcolor='white', margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)
    
    # 进出水对比表
    st.subheader("📋 进出水水质对比")
    df = pd.DataFrame({
        '指标': ['流量 (m³/hr)', 'TSS (mg/L)', 'TOC (mg/L)', '非挥发性TOC (mg/L)'],
        '进水': [f"{inlet['flow_rate']:.1f}", f"{inlet['tss_conc']:.1f}", 
                f"{inlet['toc_conc']:.1f}", f"{inlet['nonvolatile_toc_conc']:.1f}"],
        '产水': [f"{outlet['flow_rate']:.1f}", f"{outlet['tss_conc']:.1f}", 
                f"{outlet['toc_conc']:.1f}", f"{outlet['nonvolatile_toc_conc']:.1f}"],
        '去除率': [f"{perf['water_recovery']*100:.2f}%", f"{perf['tss_removal']*100:.1f}%",
                  f"{perf['toc_removal']*100:.1f}%", f"{perf['nonvolatile_toc_removal']*100:.1f}%"]
    })
    st.table(df)
    
    # 图表
    st.subheader("📈 数据可视化")
    col1, col2 = st.columns(2)
    with col1:
        fig1 = go.Figure(data=[go.Bar(
            x=['TSS', 'TOC', '非挥发性TOC'],
            y=[perf['tss_removal']*100, perf['toc_removal']*100, perf['nonvolatile_toc_removal']*100],
            marker_color=['#4CAF50', '#2196F3', '#FF9800'],
            text=[f'{perf["tss_removal"]*100:.1f}%', f'{perf["toc_removal"]*100:.1f}%', 
                  f'{perf["nonvolatile_toc_removal"]*100:.1f}%'],
            textposition='outside'
        )])
        fig1.update_layout(title='物质去除率对比', yaxis_title='去除率 (%)', 
                          yaxis_range=[0, 100], height=350)
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        fig2 = go.Figure(data=[
            go.Bar(name='进水', x=['TSS', 'TOC', '非挥发性TOC'],
                   y=[inlet['tss_conc'], inlet['toc_conc'], inlet['nonvolatile_toc_conc']],
                   marker_color='#f44336'),
            go.Bar(name='产水', x=['TSS', 'TOC', '非挥发性TOC'],
                   y=[outlet['tss_conc'], outlet['toc_conc'], outlet['nonvolatile_toc_conc']],
                   marker_color='#4CAF50')
        ])
        fig2.update_layout(title='进出水浓度对比', yaxis_title='浓度 (mg/L)', 
                          barmode='group', height=350)
        st.plotly_chart(fig2, use_container_width=True)


if __name__ == "__main__":
    main()
