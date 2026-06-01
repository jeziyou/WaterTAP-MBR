"""
WaterTAP MBR 工艺设计工具 - Streamlit 版本（兼容修复版）
==========================================================
解决 metaclass conflict 问题

安装依赖（在 Notebook 或终端中运行）:
    !pip install pyomo==6.10.0 idaes-pse==2.11.0 watertap==1.6.0 streamlit plotly --quiet
    !apt-get install -y glpk-utils -qq

运行:
    streamlit run app_streamlit.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys

# ============================================================
# 版本兼容性检查与修复
# ============================================================
def check_environment():
    """检查并显示环境信息"""
    try:
        import pyomo
        st.sidebar.caption(f"Pyomo: {pyomo.__version__}")
    except:
        st.error("❌ Pyomo 未安装。请运行: `pip install pyomo==6.10.0`")
        return False
    
    try:
        import idaes
        st.sidebar.caption(f"IDAES: {idaes.__version__}")
    except:
        st.error("❌ IDAES 未安装。请运行: `pip install idaes-pse==2.11.0`")
        return False
    
    try:
        import watertap
        st.sidebar.caption("WaterTAP: 已安装")
    except:
        st.error("❌ WaterTAP 未安装。请运行: `pip install watertap==1.6.0`")
        return False
    
    return True


# ============================================================
# WaterTAP MBR 模拟函数（带隔离导入）
# ============================================================
def run_mbr_simulation(flow_rate, tss_conc, toc_conc, nonvolatile_toc_conc,
                       water_recovery, tss_removal, toc_removal, nonvolatile_toc_removal):
    """运行 MBR 模拟"""
    try:
        # 延迟导入，避免与 Streamlit 的 pydantic 冲突
        from pyomo.environ import ConcreteModel
        from idaes.core import FlowsheetBlock
        from idaes.core.solvers import get_solver
        from watertap.core.wt_database import Database
        from watertap.core.zero_order_properties import WaterParameterBlock
        from watertap.unit_models.zero_order import MBRZO
        
        # 创建模型
        m = ConcreteModel()
        m.db = Database()
        m.fs = FlowsheetBlock(dynamic=False)
        
        # 定义组分
        solute_list = ["tss", "toc", "nonvolatile_toc"]
        m.fs.params = WaterParameterBlock(solute_list=solute_list)
        
        # 创建 MBR 单元
        m.fs.mbr = MBRZO(
            property_package=m.fs.params,
            database=m.db,
            process_subtype="default"
        )
        
        # 设置进料条件
        Q_in = flow_rate
        
        concentrations = {
            "tss": tss_conc,
            "toc": toc_conc,
            "nonvolatile_toc": nonvolatile_toc_conc,
        }
        
        m.fs.mbr.inlet.flow_mass_comp[0, "H2O"].fix(Q_in)
        
        for solute, conc_mgL in concentrations.items():
            mass_flow = (conc_mgL / 1e6) * Q_in
            m.fs.mbr.inlet.flow_mass_comp[0, solute].fix(mass_flow)
        
        m.fs.mbr.load_parameters_from_database()
        
        # 覆盖参数
        m.fs.mbr.recovery_frac_mass_H2O.fix(water_recovery)
        m.fs.mbr.removal_frac_mass_comp[0, "tss"].fix(tss_removal)
        m.fs.mbr.removal_frac_mass_comp[0, "toc"].fix(toc_removal)
        m.fs.mbr.removal_frac_mass_comp[0, "nonvolatile_toc"].fix(nonvolatile_toc_removal)
        
        # 求解
        try:
            solver = get_solver("glpk")
        except:
            solver = get_solver()
        
        result = solver.solve(m, tee=False)
        
        if str(result.solver.status) != "ok":
            return {"success": False, "error": f"求解失败: {result.solver.status}"}
        
        # 收集结果
        inlet = m.fs.mbr.inlet
        outlet = m.fs.mbr.treated
        byproduct = m.fs.mbr.byproduct
        outlet_flow = outlet.flow_mass_comp[0, "H2O"].value
        
        return {
            "success": True,
            "performance": {
                "water_recovery": m.fs.mbr.recovery_frac_mass_H2O[0].value,
                "tss_removal": m.fs.mbr.removal_frac_mass_comp[0, "tss"].value,
                "toc_removal": m.fs.mbr.removal_frac_mass_comp[0, "toc"].value,
                "nonvolatile_toc_removal": m.fs.mbr.removal_frac_mass_comp[0, "nonvolatile_toc"].value,
                "power_consumption_kw": m.fs.mbr.electricity[0].value / 1000,
                "electricity_intensity": m.fs.mbr.electricity_intensity[0].value,
            },
            "inlet": {
                "flow_rate": Q_in,
                "tss_conc": concentrations["tss"],
                "toc_conc": concentrations["toc"],
                "nonvolatile_toc_conc": concentrations["nonvolatile_toc"],
                "tss_mass": inlet.flow_mass_comp[0, "tss"].value,
                "toc_mass": inlet.flow_mass_comp[0, "toc"].value,
                "nonvolatile_toc_mass": inlet.flow_mass_comp[0, "nonvolatile_toc"].value,
            },
            "outlet": {
                "flow_rate": outlet_flow,
                "tss_conc": (outlet.flow_mass_comp[0, "tss"].value / outlet_flow) * 1e6 if outlet_flow > 0 else 0,
                "toc_conc": (outlet.flow_mass_comp[0, "toc"].value / outlet_flow) * 1e6 if outlet_flow > 0 else 0,
                "nonvolatile_toc_conc": (outlet.flow_mass_comp[0, "nonvolatile_toc"].value / outlet_flow) * 1e6 if outlet_flow > 0 else 0,
                "tss_mass": outlet.flow_mass_comp[0, "tss"].value,
                "toc_mass": outlet.flow_mass_comp[0, "toc"].value,
                "nonvolatile_toc_mass": outlet.flow_mass_comp[0, "nonvolatile_toc"].value,
            },
            "byproduct": {
                "flow_rate": byproduct.flow_mass_comp[0, "H2O"].value,
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


# ============================================================
# 主页面
# ============================================================
def main():
    st.title("🚰 WaterTAP MBR 工艺设计工具")
    st.markdown("基于 **WaterTAP** 开源平台的膜生物反应器模拟与设计")
    
    # 环境检查
    env_ok = check_environment()
    
    if not env_ok:
        st.stop()
    
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
            results = run_mbr_simulation(
                flow_rate, tss_conc, toc_conc, nonvolatile_toc_conc,
                water_recovery, tss_removal, toc_removal, nonvolatile_toc_removal
            )
        
        if results.get("success"):
            st.session_state['results'] = results
        else:
            st.error(f"模拟失败: {results.get('error')}")
            if results.get("traceback"):
                with st.expander("查看详细错误信息"):
                    st.code(results["traceback"])
            st.session_state['results'] = None
    
    results = st.session_state.get('results')
    
    if results and results.get("success"):
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
        fig.add_trace(go.Scatter(x=[1], y=[2], mode='markers+text', marker=dict(size=80, color='#4CAF50'), text=['进水'], textposition='middle center', textfont=dict(color='white', size=13)))
        fig.add_trace(go.Scatter(x=[2.5], y=[2], mode='markers+text', marker=dict(size=120, color='#2196F3'), text=['MBR'], textposition='middle center', textfont=dict(color='white', size=15)))
        fig.add_trace(go.Scatter(x=[4], y=[2.5], mode='markers+text', marker=dict(size=70, color='#8BC34A'), text=['产水'], textposition='middle center', textfont=dict(color='white', size=11)))
        fig.add_trace(go.Scatter(x=[4], y=[1.5], mode='markers+text', marker=dict(size=50, color='#FF9800'), text=['浓水'], textposition='middle center', textfont=dict(color='white', size=11)))
        fig.add_annotation(x=1.5, y=2, ax=2, ay=2, showarrow=True, arrowhead=2, arrowsize=1.5, arrowwidth=2, arrowcolor='#333')
        fig.add_annotation(x=3, y=2.3, ax=3.5, ay=2.45, showarrow=True, arrowhead=2, arrowsize=1.5, arrowwidth=2, arrowcolor='#333')
        fig.add_annotation(x=3, y=1.7, ax=3.5, ay=1.55, showarrow=True, arrowhead=2, arrowsize=1.5, arrowwidth=2, arrowcolor='#333')
        fig.add_annotation(x=1, y=1.5, text=f"Q={inlet['flow_rate']:.0f} m³/h", showarrow=False, font=dict(size=11, color='#666'))
        fig.add_annotation(x=2.5, y=1.2, text=f"P={perf['power_consumption_kw']:.1f} kW", showarrow=False, font=dict(size=11, color='#666'))
        fig.add_annotation(x=4, y=3, text=f"Q={outlet['flow_rate']:.1f} m³/h", showarrow=False, font=dict(size=11, color='#666'))
        fig.add_annotation(x=4, y=1, text=f"Q={byproduct['flow_rate']:.2f} m³/h", showarrow=False, font=dict(size=11, color='#666'))
        fig.update_layout(height=300, showlegend=False, xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0.5, 4.5]), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0.5, 3.5]), plot_bgcolor='white', margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
        
        # 进出水对比表
        st.subheader("📋 进出水水质对比")
        df = pd.DataFrame({
            '指标': ['流量 (m³/hr)', 'TSS (mg/L)', 'TOC (mg/L)', '非挥发性TOC (mg/L)'],
            '进水': [f"{inlet['flow_rate']:.1f}", f"{inlet['tss_conc']:.1f}", f"{inlet['toc_conc']:.1f}", f"{inlet['nonvolatile_toc_conc']:.1f}"],
            '产水': [f"{outlet['flow_rate']:.1f}", f"{outlet['tss_conc']:.1f}", f"{outlet['toc_conc']:.1f}", f"{outlet['nonvolatile_toc_conc']:.1f}"],
            '去除率': [f"{perf['water_recovery']*100:.2f}%", f"{perf['tss_removal']*100:.1f}%", f"{perf['toc_removal']*100:.1f}%", f"{perf['nonvolatile_toc_removal']*100:.1f}%"]
        })
        st.table(df)
        
        # 图表
        st.subheader("📈 数据可视化")
        col1, col2 = st.columns(2)
        with col1:
            fig1 = go.Figure(data=[go.Bar(x=['TSS', 'TOC', '非挥发性TOC'], y=[perf['tss_removal']*100, perf['toc_removal']*100, perf['nonvolatile_toc_removal']*100], marker_color=['#4CAF50', '#2196F3', '#FF9800'], text=[f'{perf["tss_removal"]*100:.1f}%', f'{perf["toc_removal"]*100:.1f}%', f'{perf["nonvolatile_toc_removal"]*100:.1f}%'], textposition='outside')])
            fig1.update_layout(title='物质去除率对比', yaxis_title='去除率 (%)', yaxis_range=[0, 100], height=350)
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            fig2 = go.Figure(data=[go.Bar(name='进水', x=['TSS', 'TOC', '非挥发性TOC'], y=[inlet['tss_conc'], inlet['toc_conc'], inlet['nonvolatile_toc_conc']], marker_color='#f44336'), go.Bar(name='产水', x=['TSS', 'TOC', '非挥发性TOC'], y=[outlet['tss_conc'], outlet['toc_conc'], outlet['nonvolatile_toc_conc']], marker_color='#4CAF50')])
            fig2.update_layout(title='进出水浓度对比', yaxis_title='浓度 (mg/L)', barmode='group', height=350)
            st.plotly_chart(fig2, use_container_width=True)
    
    elif results is None:
        st.info("👈 请在左侧设置参数，然后点击 **运行模拟** 按钮")
    
    # 页脚
    st.markdown("---")
    st.caption("基于 [WaterTAP](https://github.com/watertap-org/watertap) 开源平台 | Powered by Pyomo + IDAES + Streamlit")


if __name__ == "__main__":
    main()
