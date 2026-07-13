"""
Patent Application Document Generator
Generates complete patent application series:
  1. 请求书 (Request Form)
  2. 说明书 (Specification)
  3. 权利要求书 (Claims)
  4. 说明书摘要 (Abstract)
  5. 说明书附图 (Figures) - references patent_figures.pdf
"""

import os
from fpdf import FPDF

OUTPUT_DIR = r'D:\API\AI_3D_Model_Build\EVOLUTION_AI\frontend\public\docs'

# ============================================================
# Common Style
# ============================================================

class PatentPDF(FPDF):
    def __init__(self):
        super().__init__('P', 'mm', 'A4')
        self.add_font('SimSun', '', os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', 'simsun.ttc'), uni=True)
        self.add_font('SimHei', '', os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', 'simhei.ttf'), uni=True)
        self.set_auto_page_break(auto=True, margin=25)

    def header(self):
        self.set_font('SimHei', '', 9)
        self.set_text_color(128, 128, 128)
        self.cell(0, 8, '发明专利申请文件', 0, 1, 'R')
        self.line(10, 12, 200, 12)
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font('SimSun', '', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'第 {self.page_no()} 页', 0, 0, 'C')

    def title_text(self, text, size=16):
        self.set_font('SimHei', '', size)
        self.set_text_color(0, 0, 0)
        self.cell(0, 12, text, 0, 1, 'C')
        self.ln(4)

    def section_title(self, text, size=12):
        self.set_font('SimHei', '', size)
        self.set_text_color(0, 0, 0)
        self.cell(0, 10, text, 0, 1, 'L')
        self.ln(2)

    def body_text(self, text, size=10.5, indent=0):
        self.set_font('SimSun', '', size)
        self.set_text_color(0, 0, 0)
        if indent:
            self.set_x(self.l_margin + indent)
        self.multi_cell(0, 6.5, text)
        self.ln(2)

    def formula_text(self, text, size=10.5):
        self.set_font('SimSun', '', size)
        self.set_text_color(0, 0, 128)
        self.cell(0, 7, text, 0, 1, 'C')
        self.ln(1)

    def table_row(self, label, value, label_w=50):
        self.set_font('SimHei', '', 10.5)
        self.set_text_color(0, 0, 0)
        self.cell(label_w, 8, label, 1, 0, 'L')
        self.set_font('SimSun', '', 10.5)
        self.cell(0, 8, value, 1, 1, 'L')


# ============================================================
# 1. 请求书
# ============================================================

def generate_request_form():
    pdf = PatentPDF()
    pdf.add_page()
    pdf.title_text('发明专利请求书', 18)
    pdf.ln(4)

    items = [
        ('发明名称', '一种基于硬点驱动与三区混合截面的汽车A级曲面参数化生成方法'),
        ('申请人', '（请填写）'),
        ('申请人地址', '（请填写）'),
        ('发明人', '（请填写）'),
        ('联系人', '（请填写）'),
        ('联系电话', '（请填写）'),
        ('代理机构', '（请填写）'),
        ('代理人', '（请填写）'),
        ('申请文件清单', '请求书1份、说明书1份、权利要求书1份、说明书摘要1份、说明书附图1份'),
        ('附图清单', 'Fig.1~Fig.12共12幅'),
    ]

    for label, value in items:
        pdf.table_row(label, value)

    pdf.ln(6)
    pdf.section_title('声明')
    pdf.body_text('1. 本申请人声明，以上各项均真实可靠，并愿意承担因不真实而引起的法律责任。')
    pdf.body_text('2. 本申请人声明，该发明没有违反国家法律、社会公德或者妨害公共利益。')
    pdf.body_text('3. 本申请人声明，该发明不涉及国家安全或者重大利益。')

    pdf.ln(10)
    pdf.set_font('SimSun', '', 10.5)
    pdf.cell(0, 8, '申请人签章：________________          日期：____年____月____日', 0, 1, 'R')

    path = os.path.join(OUTPUT_DIR, 'patent_request.pdf')
    pdf.output(path)
    print(f'Saved: {path}')
    return path


# ============================================================
# 2. 说明书
# ============================================================

def generate_specification():
    pdf = PatentPDF()
    pdf.add_page()

    # Title
    pdf.title_text('一种基于硬点驱动与三区混合截面的\n汽车A级曲面参数化生成方法', 14)
    pdf.ln(2)

    # 技术领域
    pdf.section_title('【技术领域】')
    pdf.body_text(
        '本发明属于计算机辅助几何设计（CAGD）领域，具体涉及一种基于硬点驱动与三区混合截面的'
        '汽车A级曲面参数化生成方法，可用于汽车造型设计中的车身曲面快速生成与实时参数化修改。'
    )

    # 背景技术
    pdf.section_title('【背景技术】')
    pdf.body_text(
        '汽车车身曲面设计是汽车开发流程中的关键环节，传统方法依赖设计师手工调整NURBS控制点，'
        '设计周期长、修改成本高。现有参数化建模方法存在以下不足：\n\n'
        '（1）参数维度不足：现有方法通常仅提供5~10个全局参数，无法精确控制车身各区域的局部特征；\n\n'
        '（2）截面定义粗糙：采用简单椭圆或矩形截面，无法表达腰线、肩线等特征线的锐度变化；\n\n'
        '（3）区域混合生硬：发动机舱、乘员舱、行李箱三个区域采用统一截面参数，无法体现各区域不同的'
        '造型特征；\n\n'
        '（4）曲面质量不可控：缺乏G0/G1连续性检测和斑马纹可视化手段，无法保证A级曲面质量；\n\n'
        '（5）实时性不足：参数修改后需重新生成整个模型，延迟通常超过100ms，无法实现滑块式实时交互。'
    )

    # 发明内容
    pdf.section_title('【发明内容】')
    pdf.body_text(
        '为解决上述技术问题，本发明提供一种基于硬点驱动与三区混合截面的汽车A级曲面参数化生成方法，'
        '通过18个主硬点参数推导16个二级硬点，定义17点侧视上轮廓和15点俯视宽度双包络，'
        '采用三区乘积分解归一化混合31点精细截面，实现从参数到A级曲面的实时生成。'
    )

    pdf.section_title('【技术方案】', 11)
    pdf.body_text(
        '本发明的技术方案包括以下步骤：\n\n'
        'S1、建立主硬点参数体系，包含18个几何参数，涵盖基础尺寸（车长L、车宽W、车高H）、'
        '底盘布局（前悬FO、后悬RO、轴距WB）、车轮参数（轮距TW、轮径WR、离地间隙GC）、'
        '车身形态（腰线高度WL、肩宽比shoulderW、内倾角CA、门线高度doorLineH）、'
        '车窗角度（风挡角AA、后窗角RA）及造型细节（车头锐度noseSharp、车尾锐度tailSharp、'
        '轮拱凸起archBulge、前翼子板力度fenderFront、后翼子板力度fenderRear、侧裙深度sideSkirt）六类参数；\n\n'
        'S2、从所述18个主参数通过三角函数关系推导16个二级硬点，包括前轮心X坐标fwx=FO、'
        '后轮心X坐标rwx=L-RO、轮心Y坐标wcy=GC+WR、前轮心Z坐标fwz=TW/2+WR×0.35、'
        '车头尖端Y坐标noseTipY=GC+0.43、引擎盖Y坐标hoodY=GC+0.66、腰线Y坐标waistY=GC+WL、'
        'A柱底X坐标aBaseX=fwx+0.10、A柱顶Y坐标aTopY=H×0.92、'
        'A柱顶X坐标aTopX=aBaseX+(aTopY-waistY)/tan(AA)、车顶Y坐标roofY=H、'
        'C柱底X坐标cBaseX=rwx+0.30、C柱顶Y坐标cTopY=aTopY-0.03、'
        'C柱顶X坐标cTopX=cBaseX-max(0.1,cTopY-waistY)/tan(RA)、'
        '车顶峰值X坐标roofPeakX=(aTopX+cTopX)/2，并施加引擎盖高度约束'
        '（hoodY=GC+0.66，若hoodY≥waistY则hoodY=waistY-0.05）；\n\n'
        'S3、定义由17个关键点构成的侧视上轮廓和由15个关键点构成的俯视宽度包络，'
        '在相邻关键点之间采用smoothstep插值函数S(t)=3t²-2t³进行C1连续插值，形成双包络约束；\n\n'
        'S4、在每个纵向站位X处，计算引擎盖区、乘员舱区、行李箱区三区权重，'
        '通过乘积分解（hoodOnly=hoodF×(1-cabinF)×(1-trunkF)、cabinOnly=cabinF、'
        'trunkOnly=trunkF×(1-cabinF)×(1-hoodF)）归一化确保权重和为1；\n\n'
        'S5、根据所述三区权重，混合三区独立的5层截面参数（底部半宽botHW、门槛半宽sillHW、'
        '腰线半宽waistHW、肩线半宽shldHW、车顶半宽roofHW），其中乘员舱车顶半宽通过tumblehome'
        '内倾效应计算（cRoofHW=hw×max(0.25,shoulderW×0.45-sin(CA)×0.15)），生成31点闭合截面；\n\n'
        'S6、对所述31点闭合截面进行弧长参数化重采样，在特征段（k=6~11及k=19~24，即腰线至肩线区域）'
        '采用线性插值保持锐度，在其余段采用smoothstep插值保持光滑；\n\n'
        'S7、对截面顶点施加轮拱切割（archCircleY=archBotY+√(1-(d/archR)²)×(archTopY-archBotY)，'
        '双向smoothstep衰减）、翼子板凸起（bulgeAmt=0.03×aggression×(1-d/range)²，'
        '垂直递减：门槛100%→腰线50%→肩线30%）、侧裙收窄及车头/尾锥形收窄'
        '（taperCoeff=0.55+sharpness×0.25，各层宽度乘以(1-endFactor×(taper-levelOffset))，'
        'offset从底部0递增至车顶0.05）等后处理；\n\n'
        'S8、生成相邻纵向站位与截面站位之间的三角面片索引，构成完整车身曲面；\n\n'
        'S9、玻璃曲面基于二级硬点生成，前风挡采用余弦鼓包'
        '（bulge=WBulge×cos(s×π)×(1-t×0.5)），后窗采用反向余弦鼓包'
        '（bulge=WBulge×0.8×cos(s×π)×t×0.5），侧窗以B柱为界分前后两片；\n\n'
        'S10、曲面质量通过边共享率检测G0/G1连续性，并以斑马纹着色器'
        '（stripe=smoothstep(0.02,0.04,|mod(reflectX×10,0.2)-0.1|)）可视化连续性断裂。'
    )

    pdf.section_title('【有益效果】', 11)
    pdf.body_text(
        '（1）参数维度高：18个主参数+16个二级硬点，提供充分的设计自由度，'
        '可精确控制车身各区域的局部特征；\n\n'
        '（2）截面精细：31点闭合截面+弧长参数化+特征线感知插值，'
        '可表达腰线、肩线等特征线的锐度变化；\n\n'
        '（3）区域混合自然：三区乘积分解归一化，各区域独立参数控制，'
        '过渡区域平滑无缝；\n\n'
        '（4）曲面质量可控：G0/G1连续性检测+斑马纹可视化，保证A级曲面质量；\n\n'
        '（5）实时交互：18参数到A级曲面的完整管线更新延迟低于20ms，'
        '实现滑块式实时参数化修改。'
    )

    # 附图说明
    pdf.section_title('【附图说明】')
    figures = [
        ('Fig. 1', '算法总览图，包含6个子图：(a)侧视上轮廓与二级硬点、(b)俯视宽度轮廓、(c)三区混合权重、(d)三区截面、(e)3D线框、(f)3D曲面'),
        ('Fig. 2', '正交三视图，包含(a)侧视图、(b)俯视图、(c)前视图'),
        ('Fig. 3', '带尺寸标注的侧视轮廓图，标注了L/WB/H尺寸、A/C柱硬点位置、腰线和引擎盖高度'),
        ('Fig. 4', '8站位截面演化图，从车头到车尾展示各站位的三区权重H/C/T和截面形状变化'),
        ('Fig. 5', '6角度3D曲面渲染图，包含(a)透视、(b)正视、(c)侧视、(d)俯视、(e)前45°、(f)后45°'),
        ('Fig. 6', 'Smoothstep插值函数图，包含(a)S(t)=3t²-2t³曲线及端点导数标注、(b)侧视轮廓线性与smoothstep插值对比、(c)顶宽轮廓线性与smoothstep插值对比'),
        ('Fig. 7', '31点截面与特征线感知插值图，包含(a)31点截面关键点标注及特征段k=6~11,19~24着色、(b)弧长参数化重采样结果'),
        ('Fig. 8', '轮拱切割算法图，包含(a)四分之一圆弧√(1-(d/R)²)几何、(b)双向smoothstep衰减曲线、(c)前轮位置截面切割前后对比'),
        ('Fig. 9', '翼子板凸起算法图，包含(a)二次衰减曲线(1-d/R)²、(b)垂直递减分布100%→50%→30%、(c)俯视翼子板影响区域'),
        ('Fig. 10', '玻璃曲面生成图，包含(a)3D玻璃曲面、(b)前风挡余弦鼓包cos(sπ)(1-t×0.5)、(c)后窗反向余弦鼓包、(d)侧视玻璃位置'),
        ('Fig. 11', '曲面质量分析图，包含(a)斑马纹着色器函数、(b)车身斑马纹模拟、(c)G0/G1连续性检测结果'),
        ('Fig. 12', '算法管线与性能图，包含(a)7步管线流程图及各步延迟标注、(b)各阶段性能柱状图'),
    ]
    for fig_num, desc in figures:
        pdf.set_font('SimHei', '', 10.5)
        pdf.cell(20, 6.5, fig_num)
        pdf.set_font('SimSun', '', 10.5)
        pdf.multi_cell(0, 6.5, '  ' + desc)
        pdf.ln(1)

    # 具体实施方式
    pdf.section_title('【具体实施方式】')

    pdf.section_title('实施例1：整体方法流程', 11)
    pdf.body_text(
        '参照Fig.1，本实施例提供一种基于硬点驱动与三区混合截面的汽车A级曲面参数化生成方法，'
        '包括以下步骤S1~S8。\n\n'
        'S1中，建立的主硬点参数体系包含18个几何参数，默认值为：L=4.9m, W=1.85m, H=1.42m, '
        'FO=0.85m, RO=1.15m, WB=2.9m, TW=1.55m, WR=0.38m, GC=0.12m, WL=0.52m, '
        'shoulderW=0.85, CA=8.0°, doorLineH=0.48m, AA=32.0°, RA=28.0°, '
        'noseSharp=0.6, tailSharp=0.55, archBulge=0.12, fenderFront=0.7, '
        'fenderRear=0.65, sideSkirt=0.08。\n\n'
        'S2中，推导的16个二级硬点为：fwx=0.85, rwx=3.75, wcy=0.50, fwz=0.895, '
        'noseTipY=0.55, hoodY=0.78, waistY=0.64, aBaseX=0.95, aTopY=1.306, '
        'aTopX=2.016, roofY=1.42, cBaseX=4.05, cTopY=1.276, cTopX=2.853, '
        'roofPeakX=2.435, cBaseY=0.66。其中hoodY=0.78<waistY=0.64不成立，'
        '因此hoodY被约束为0.64-0.05=0.59。\n\n'
        'S3中，17点侧视上轮廓和15点俯视宽度包络的关键点坐标如Fig.1(a)(b)所示，'
        'smoothstep函数S(t)=3t²-2t³在t=0和t=1处导数为零，保证C1连续性。\n\n'
        'S4中，三区权重通过乘积分解归一化计算，如Fig.1(c)和Fig.4所示，'
        '各站位的三区权重H/C/T标注在截面标题中。\n\n'
        'S5中，31点闭合截面的5层参数经三区混合后生成，如Fig.7(a)所示，'
        '其中乘员舱车顶半宽通过tumblehome效应缩减。\n\n'
        'S6中，弧长参数化重采样结果如Fig.7(b)所示，红色段为线性插值的特征段，蓝色段为smoothstep插值的光滑段。\n\n'
        'S7中，后处理效果如Fig.8、Fig.9所示。\n\n'
        'S8中，生成的完整车身曲面包含5184个顶点和10240个三角面，如Fig.5所示。'
    )

    pdf.section_title('实施例2：几何约束条件', 11)
    pdf.body_text(
        '参照Fig.3，本实施例说明引擎盖高度约束条件的具体实现。\n\n'
        '引擎盖Y坐标初始计算为hoodY=GC+0.66=0.12+0.66=0.78m。'
        '腰线Y坐标为waistY=GC+WL=0.12+0.52=0.64m。由于hoodY=0.78≥waistY=0.64，'
        '触发约束条件，hoodY被修正为waistY-0.05=0.59m，确保引擎盖始终低于腰线，'
        '符合汽车造型设计的基本规则。Fig.3中标注了Waistline=0.640m和Hood=0.590m，'
        '清晰展示了约束条件的执行结果。'
    )

    pdf.section_title('实施例3：Smoothstep插值函数', 11)
    pdf.body_text(
        '参照Fig.6，本实施例说明smoothstep插值函数的具体应用。\n\n'
        'Smoothstep函数定义为S(t)=3t²-2t³，其中t∈[0,1]。该函数在t=0处S(0)=0、S\'(0)=0，'
        '在t=1处S(1)=1、S\'(1)=0，保证了C1连续性。\n\n'
        'Fig.6(a)展示了S(t)曲线与线性函数y=t的对比，可见smoothstep在端点处平滑过渡。'
        'Fig.6(b)展示了侧视上轮廓的线性插值与smoothstep插值对比，smoothstep在关键点处'
        '消除了折角，产生更光滑的轮廓线。Fig.6(c)展示了俯视宽度轮廓的类似对比效果。'
    )

    pdf.section_title('实施例4：三区乘积分解归一化', 11)
    pdf.body_text(
        '参照Fig.4，本实施例说明三区乘积分解归一化的具体计算过程。\n\n'
        '在每个纵向站位x处，首先计算三个原始权重：\n'
        'hoodF=1-S((x-aBaseX+0.2)/0.4)\n'
        'cabinF=S((x-aTopX+0.15)/0.3)×(1-S((x-cTopX-0.15)/0.3))\n'
        'trunkF=S((x-cBaseX+0.2)/0.4)\n\n'
        '然后通过乘积分解实现互斥：\n'
        'hoodOnly=hoodF×(1-cabinF)×(1-trunkF)\n'
        'cabinOnly=cabinF\n'
        'trunkOnly=trunkF×(1-cabinF)×(1-hoodF)\n\n'
        '最后归一化：hoodOnly/=sumF, cabinOnly/=sumF, trunkOnly/=sumF，确保权重和恒为1。\n\n'
        'Fig.4展示了8个典型站位的截面形状及三区权重标注，如车头处H/C/T=1.0/0.0/0.0，'
        '车顶处H/C/T=0.0/1.0/0.0，车尾处H/C/T=0.0/0.0/1.0，过渡区域三区权重平滑渐变。'
    )

    pdf.section_title('实施例5：Tumblehome内倾效应', 11)
    pdf.body_text(
        '参照Fig.7(a)，本实施例说明tumblehome内倾效应的具体计算。\n\n'
        '乘员舱车顶半宽通过tumblehome角缩减：\n'
        'cRoofHW=hw×max(0.25, shoulderW×0.45-sin(CA_rad)×0.15)\n\n'
        '其中CA_rad为内倾角CA的弧度值，hw为该站位处的局部半宽，shoulderW为肩宽比参数。'
        '当CA=8°时，sin(8°×π/180)=0.139，cRoofHW=0.925×max(0.25, 0.383-0.021)=0.925×0.362=0.335m，'
        '小于肩线半宽0.613m，实现了车顶内收的效果。Fig.7(a)标题中标注了CA=8°和roofHW=0.335m。'
    )

    pdf.section_title('实施例6：特征线感知插值', 11)
    pdf.body_text(
        '参照Fig.7，本实施例说明特征线感知插值的具体实现。\n\n'
        '31点闭合截面中，第k=6~11段（右侧腰线至肩线区域）和第k=19~24段（左侧对称区域）'
        '被识别为特征线段。在特征线段上采用线性插值ss=frac，保持特征线锐度；'
        '在其余段上采用smoothstep插值ss=frac²×(3-2×frac)，保持曲面光滑。\n\n'
        'Fig.7(a)中红色线段为特征段（k=6~11, 19~24），蓝色线段为光滑段。'
        'Fig.7(b)展示了弧长参数化重采样后的65点截面，红色段保持锐利特征，蓝色段保持光滑过渡。'
    )

    pdf.section_title('实施例7：轮拱切割算法', 11)
    pdf.body_text(
        '参照Fig.8，本实施例说明轮拱切割算法的具体实现。\n\n'
        '轮拱半径archR=WR×(1.0+archBulge×0.8)=0.38×(1.0+0.12×0.8)=0.417m。'
        '四分之一圆弧形状由archCircleY=archBotY+√(1-(d/archR)²)×(archTopY-archBotY)定义，'
        '如Fig.8(a)所示。\n\n'
        '双向smoothstep衰减如Fig.8(b)所示：纵向衰减archFade=1-S(d/archR)从轮心向外递减，'
        '横向衰减sideFade=S((|z|-innerZ)/(hw×0.95-innerZ))从轮拱内侧向外递增，'
        '合成深度depth=archFade×sideFade。\n\n'
        'Fig.8(c)展示了前轮位置（x=0.85m）截面切割前后的对比，蓝色虚线为切割前截面，'
        '红色实线为切割后截面，可见轮拱区域的半圆弧切口。'
    )

    pdf.section_title('实施例8：翼子板凸起算法', 11)
    pdf.body_text(
        '参照Fig.9，本实施例说明翼子板凸起算法的具体实现。\n\n'
        '翼子板影响范围fenderRange=WR×1.8=0.38×1.8=0.684m。凸起量采用二次衰减：\n'
        'bulgeAmt=0.03×aggression×(1-d/fenderRange)²\n\n'
        'Fig.9(a)展示了前翼子板（aggression=0.7）和后翼子板（aggression=0.65）的衰减曲线。'
        'Fig.9(b)展示了垂直递减分布：门槛层增加bulgeAmt×hw×100%，腰线层增加50%，肩线层增加30%。'
        'Fig.9(c)展示了俯视图中前后翼子板的影响区域圆。'
    )

    pdf.section_title('实施例9：车头/尾锥形收窄', 11)
    pdf.body_text(
        '参照Fig.3，本实施例说明车头/尾锥形收窄算法的具体实现。\n\n'
        '可变锥度系数noseTaper=0.55+noseSharp×0.25=0.55+0.6×0.25=0.70。'
        '端部因子endF=noseF+tailF，其中noseF=1-S(x/(0.15+noseSharp×0.35))，'
        'tailF=S((x-L+0.15+tailSharp×0.35)/(0.15+tailSharp×0.35))。\n\n'
        '各层宽度乘以缩减因子width×=(1-endF×(taper-levelOffset))，'
        'levelOffset从底部到车顶递增：底部0、门槛0.1、腰线0.15、肩线0.15、车顶0.05，'
        '实现从底部最大收窄到车顶最小收窄的递减排窄效果。Fig.3中可见车头和车尾的逐渐收窄。'
    )

    pdf.section_title('实施例10：玻璃曲面生成', 11)
    pdf.body_text(
        '参照Fig.10，本实施例说明玻璃曲面生成的具体实现。\n\n'
        '前风挡基于A柱底(aBaseX,waistY)至A柱顶(aTopX,aTopY)生成21×21参数化曲面，'
        '宽度为车宽的82%，施加余弦鼓包bulge=WBulge×cos(s×π)×(1-t×0.5)，'
        '鼓包在横向呈余弦分布、在纵向从底到顶递减50%，如Fig.10(b)所示。\n\n'
        '后窗基于C柱底(cBaseX,waistY)至C柱顶(cTopX,cTopY)生成21×21参数化曲面，'
        '宽度为车宽的78%，施加反向余弦鼓包bulge=WBulge×0.8×cos(s×π)×t×0.5，'
        '鼓包在纵向从底到顶递增，如Fig.10(c)所示。\n\n'
        '侧窗以B柱位置x=(aBaseX+cBaseX)/2为界分为前门窗和后门窗两片，'
        '位于z=±(W/2+0.003)处。Fig.10(d)展示了玻璃在侧视轮廓中的位置。'
    )

    pdf.section_title('实施例11：曲面质量分析', 11)
    pdf.body_text(
        '参照Fig.11，本实施例说明曲面质量分析的具体实现。\n\n'
        'G0位置连续性检测：枚举所有网格边并计数，若每条边均被恰好两个三角形共享，则判定达到G0连续性。'
        '由于车身曲面在首尾截面处存在开放边，G0连续性为FAIL，这是正常现象。\n\n'
        'G1切线连续性检测：计算共享边数与总边数的比率，本实施例中共享边率为98.1%，超过95%阈值，'
        '判定达到G1连续性，如Fig.11(c)所示。\n\n'
        '斑马纹可视化：采用GLSL着色器计算stripe=smoothstep(0.02,0.04,|mod(reflectX×10,0.2)-0.1|)，'
        '其中reflectX为视线方向反射向量的X分量。条纹断裂或偏移处指示G1/G2连续性断裂，'
        '如Fig.11(a)(b)所示。'
    )

    pdf.section_title('实施例12：实时参数化修改', 11)
    pdf.body_text(
        '参照Fig.12，本实施例说明实时参数化修改的具体实现。\n\n'
        '当18个主硬点参数中任一参数被修改时，自动触发以下完整管线的重新执行：\n'
        '（1）deriveHardpoints()重算16个二级硬点，延迟<1ms；\n'
        '（2）sideUpperProfile()和topWidthProfile()重生成双包络轮廓，延迟<1ms；\n'
        '（3）computeZoneWeights()计算80个站位的三区权重，延迟<1ms；\n'
        '（4）generate31PointCrossSection()+arcLengthParameterization()生成80×64网格，延迟<5ms；\n'
        '（5）后处理（轮拱+翼子板+锥形+侧裙），延迟<3ms；\n'
        '（6）createBody()组装5184顶点10240三角面，延迟<10ms；\n'
        '（7）createGlass()重生成4面玻璃曲面，延迟<2ms。\n\n'
        '整体管线延迟低于20ms，实现参数滑块与三维模型的实时联动，如Fig.12(b)的性能柱状图所示。'
    )

    path = os.path.join(OUTPUT_DIR, 'patent_specification.pdf')
    pdf.output(path)
    print(f'Saved: {path}')
    return path


# ============================================================
# 3. 权利要求书
# ============================================================

def generate_claims():
    pdf = PatentPDF()
    pdf.add_page()
    pdf.title_text('权 利 要 求 书', 16)

    claims = [
        # Claim 1
        '1. 一种基于硬点驱动与三区混合截面的汽车A级曲面参数化生成方法，其特征在于，包括以下步骤：\n\n'
        'S1、建立主硬点参数体系，包含18个几何参数，所述参数包括：车长L、车宽W、车高H、前悬FO、'
        '后悬RO、轴距WB、轮距TW、轮径WR、离地间隙GC、腰线高度WL、风挡角AA、内倾角CA、'
        '后窗角RA、肩宽比shoulderW、门线高度doorLineH、车头锐度noseSharp、车尾锐度tailSharp、'
        '轮拱凸起archBulge；\n\n'
        'S2、从所述18个主参数通过三角函数关系推导16个二级硬点，包括：前轮心X坐标fwx=FO、'
        '后轮心X坐标rwx=L-RO、轮心Y坐标wcy=GC+WR、前轮心Z坐标fwz=TW/2+WR×0.35、'
        '车头尖端Y坐标noseTipY=GC+0.43、引擎盖Y坐标hoodY=GC+0.66、腰线Y坐标waistY=GC+WL、'
        'A柱底X坐标aBaseX=fwx+0.10、A柱顶Y坐标aTopY=H×0.92、'
        'A柱顶X坐标aTopX=aBaseX+(aTopY-waistY)/tan(AA)、车顶Y坐标roofY=H、'
        'C柱底X坐标cBaseX=rwx+0.30、C柱顶Y坐标cTopY=aTopY-0.03、'
        'C柱顶X坐标cTopX=cBaseX-max(0.1,cTopY-waistY)/tan(RA)、'
        '车顶峰值X坐标roofPeakX=(aTopX+cTopX)/2；\n\n'
        'S3、定义由17个关键点构成的侧视上轮廓和由15个关键点构成的俯视宽度包络，'
        '在相邻关键点之间采用smoothstep插值函数S(t)=3t²-2t³进行C1连续插值，形成双包络约束；\n\n'
        'S4、在每个纵向站位X处，计算引擎盖区、乘员舱区、行李箱区三区权重，并进行乘积分解归一化：'
        'hoodOnly=hoodF×(1-cabinF)×(1-trunkF)，cabinOnly=cabinF，'
        'trunkOnly=trunkF×(1-cabinF)×(1-hoodF)，各权重除以三者之和确保归一化；\n\n'
        'S5、根据所述三区权重，混合三区独立的5层截面参数（底部半宽botHW、门槛半宽sillHW、'
        '腰线半宽waistHW、肩线半宽shldHW、车顶半宽roofHW），生成31点闭合截面；\n\n'
        'S6、对所述31点闭合截面进行弧长参数化重采样，在特征段采用线性插值保持锐度，'
        '在非特征段采用smoothstep插值保持光滑；\n\n'
        'S7、对截面顶点施加轮拱切割、翼子板凸起、侧裙收窄及车头/尾锥形收窄后处理；\n\n'
        'S8、生成相邻纵向站位与截面站位之间的三角面片索引，构成完整车身曲面。',

        # Claim 2
        '2. 根据权利要求1所述的方法，其特征在于，所述S2中还包括几何约束条件：'
        '引擎盖Y坐标hoodY=GC+0.66，若hoodY≥waistY则令hoodY=waistY-0.05，'
        '确保引擎盖高度低于腰线高度。',

        # Claim 3
        '3. 根据权利要求1所述的方法，其特征在于，所述S3中smoothstep插值函数为S(t)=3t²-2t³，'
        '其中t为相邻关键点之间的归一化参数t∈[0,1]，该函数在t=0和t=1处导数为零，保证C1连续性。',

        # Claim 4
        '4. 根据权利要求1所述的方法，其特征在于，所述S4中三区权重的计算方法为：\n\n'
        '引擎盖区权重：hoodF=1-S((x-aBaseX+0.2)/0.4)，其中S为smoothstep函数；\n\n'
        '乘员舱区权重：cabinF=S((x-aTopX+0.15)/0.3)×(1-S((x-cTopX-0.15)/0.3))；\n\n'
        '行李箱区权重：trunkF=S((x-cBaseX+0.2)/0.4)；\n\n'
        '通过乘积分解hoodOnly=hoodF×(1-cabinF)×(1-trunkF)、cabinOnly=cabinF、'
        'trunkOnly=trunkF×(1-cabinF)×(1-hoodF)实现互斥分解，'
        '再除以三者之和sumF=hoodOnly+cabinOnly+trunkOnly实现归一化，确保三区权重之和恒为1。',

        # Claim 5
        '5. 根据权利要求1所述的方法，其特征在于，所述S5中乘员舱区的车顶半宽通过tumblehome'
        '内倾效应计算：cRoofHW=hw×max(0.25,shoulderW×0.45-sin(CA_rad)×0.15)，'
        '其中CA_rad为内倾角CA的弧度值，hw为该站位处的局部半宽，shoulderW为肩宽比参数，'
        'sin(CA_rad)将内倾角转换为宽度缩减量，角度越大车顶越窄。',

        # Claim 6
        '6. 根据权利要求1所述的方法，其特征在于，所述S6中特征线感知插值的具体方法为：\n\n'
        '将31点闭合截面中第k=6~11段（右侧腰线至肩线区域）和第k=19~24段（左侧对称区域）'
        '识别为特征线段，在所述特征线段上采用线性插值ss=frac保持特征线锐度；\n\n'
        '在其余非特征段上采用smoothstep插值ss=frac²×(3-2×frac)保持曲面光滑；\n\n'
        '其中frac为弧长参数化中目标弧长在对应段内的归一化位置参数。',

        # Claim 7
        '7. 根据权利要求1所述的方法，其特征在于，所述S7中轮拱切割算法为：\n\n'
        '检测顶点是否在轮拱影响区内：|x-wheelCenterX|<WR×1.5；\n\n'
        '计算轮拱半径：archR=WR×(1.0+archBulge×0.8)；\n\n'
        '计算四分之一圆弧形状：archCircleY=archBotY+√(max(0,1-(dist/archR)²))×(archTopY-archBotY)；\n\n'
        '施加双向smoothstep衰减：纵向衰减archFade=1-S(archDist/archR)，'
        '横向衰减sideFade=S((|z|-archInnerZ)/(hw×0.95-archInnerZ))，'
        '合成深度depth=archFade×sideFade；\n\n'
        '对位于拱形下方的顶点进行位移：y=y+(archCircleY-y)×depth×(0.7+archBulge×1.5)。',

        # Claim 8
        '8. 根据权利要求1所述的方法，其特征在于，所述S7中翼子板凸起算法为：\n\n'
        '在轮心前后fenderRange=WR×1.8范围内施加凸起；\n\n'
        '凸起量采用二次衰减：bulgeAmt=0.03×fenderAggression×(1-dist/fenderRange)²；\n\n'
        '垂直方向递减分布：门槛层sillHW增加bulgeAmt×hw×100%，腰线层waistHW增加bulgeAmt×hw×50%，'
        '肩线层shldHW增加bulgeAmt×hw×30%，从底部到顶部递减，营造翼子板肌肉感。',

        # Claim 9
        '9. 根据权利要求1所述的方法，其特征在于，所述S7中车头/尾锥形收窄算法为：\n\n'
        '计算可变锥度系数：noseTaper=0.55+noseSharp×0.25，tailTaper=0.55+tailSharp×0.25；\n\n'
        '计算端部因子endF=noseF+tailF，其中noseF=1-S(x/(0.15+noseSharp×0.35))，'
        'tailF=S((x-L+0.15+tailSharp×0.35)/(0.15+tailSharp×0.35))；\n\n'
        '各层宽度乘以缩减因子width×=(1-endF×(taper-levelOffset))，其中levelOffset从底部到车顶递增：'
        '底部offset=0、门槛offset=0.1、腰线offset=0.15、肩线offset=0.15、车顶offset=0.05，'
        '实现从底部最大收窄到车顶最小收窄的递减排窄。',

        # Claim 10
        '10. 根据权利要求1所述的方法，其特征在于，还包括玻璃曲面生成步骤：\n\n'
        '前风挡：基于二级硬点中A柱底(aBaseX,waistY)至A柱顶(aTopX,aTopY)生成10×10参数化曲面，'
        '宽度为车宽的82%，施加余弦鼓包bulge=WBulge×cos(s×π)×(1-t×0.5)，'
        '其中s为横向参数、t为纵向参数，鼓包在横向呈余弦分布、在纵向从底到顶递减50%；\n\n'
        '后窗：基于C柱底(cBaseX,waistY)至C柱顶(cTopX,cTopY)生成10×10参数化曲面，'
        '宽度为车宽的78%，施加反向余弦鼓包bulge=WBulge×0.8×cos(s×π)×t×0.5，'
        '鼓包在纵向从底到顶递增；\n\n'
        '侧窗：以B柱位置x=(aBaseX+cBaseX)/2为界分为前门窗和后门窗两片，'
        '位于z=±(W/2+0.003)处，各为10段条带网格。',

        # Claim 11
        '11. 根据权利要求1所述的方法，其特征在于，还包括曲面质量分析步骤：\n\n'
        'G0位置连续性检测：枚举所有网格边并计数，若每条边均被恰好两个三角形共享，则判定达到G0连续性；\n\n'
        'G1切线连续性检测：计算共享边数与总边数的比率，若该比率超过95%则判定达到G1连续性；\n\n'
        '斑马纹可视化：采用GLSL着色器计算基于反射向量的条纹'
        'stripe=smoothstep(0.02,0.04,|mod(reflectX×10,0.2)-0.1|)，'
        '其中reflectX为视线方向反射向量的X分量，条纹断裂或偏移处指示G1/G2连续性断裂。',

        # Claim 12
        '12. 根据权利要求1所述的方法，其特征在于，还包括实时参数化修改步骤：\n\n'
        '当18个主硬点参数中任一参数被修改时，自动触发以下完整管线的重新执行：'
        'deriveHardpoints()重算16个二级硬点、sideUpperProfile()和topWidthProfile()重生成双包络轮廓、'
        'createBody()重生成80×64网格即5184个顶点和10240个三角面、'
        'createGlass()重生成4面玻璃曲面，整体更新延迟低于20ms，实现参数滑块与三维模型的实时联动。',
    ]

    for claim in claims:
        pdf.body_text(claim)
        pdf.ln(3)

    path = os.path.join(OUTPUT_DIR, 'patent_claims.pdf')
    pdf.output(path)
    print(f'Saved: {path}')
    return path


# ============================================================
# 4. 说明书摘要
# ============================================================

def generate_abstract():
    pdf = PatentPDF()
    pdf.add_page()
    pdf.title_text('说明书摘要', 16)

    pdf.body_text(
        '一种基于硬点驱动与三区混合截面的汽车A级曲面参数化生成方法，属于计算机辅助几何设计领域。'
        '该方法首先建立包含18个几何参数的主硬点参数体系，涵盖基础尺寸、底盘布局、车轮参数、'
        '车身形态、车窗角度及造型细节六类参数；其次通过三角函数关系从主参数推导出16个二级硬点，'
        '其中A柱顶X坐标由风挡角反算(aTopX=aBaseX+(aTopY-waistY)/tan(AA))，'
        'C柱顶X坐标由后窗角反算(cTopX=cBaseX-max(0.1,cTopY-waistY)/tan(RA))，'
        '车顶峰值取A/C柱顶中点，并施加引擎盖高度必须低于腰线的几何约束'
        '（hoodY=GC+0.66，若hoodY≥waistY则hoodY=waistY-0.05）；'
        '然后定义17点侧视上轮廓与15点俯视宽度包络，采用smoothstep函数(3t²-2t³)进行C1连续插值'
        '形成双包络约束；在每个纵向站位计算引擎盖/乘员舱/行李箱三区权重，'
        '通过乘积分解(hoodOnly=hoodF×(1-cabinF)×(1-trunkF))归一化确保权重和为1，'
        '按权重混合三区独立的5层截面参数，其中乘员舱车顶半宽通过tumblehome角正弦值缩减'
        '(cRoofHW=hw×max(0.25,shoulderW×0.45-sin(CA)×0.15))实现内倾效应；'
        '生成31点闭合截面后进行弧长参数化，在特征段(k=6~11及k=19~24，即腰线至肩线区域)'
        '采用线性插值保持锐度，其余段采用smoothstep保持光滑；'
        '最后施加轮拱切割(archCircleY=archBotY+√(1-(d/archR)²)×(archTopY-archBotY)，双向smoothstep衰减)、'
        '翼子板凸起(bulgeAmt=0.03×aggression×(1-d/range)²，垂直递减：门槛100%→腰线50%→肩线30%)、'
        '侧裙收窄及车头/尾锥形收窄(taperCoeff=0.55+sharpness×0.25，'
        '各层宽度乘以(1-endFactor×(taper-levelOffset))，offset从底部0递增至车顶0.05)等后处理；'
        '玻璃曲面基于二级硬点生成，前风挡采用余弦鼓包(WBulge×cos(sπ)×(1-t×0.5))，'
        '后窗采用反向余弦鼓包(WBulge×0.8×cos(sπ)×t×0.5)，侧窗以B柱为界分前后两片；'
        '曲面质量通过边共享率检测G0/G1连续性，并以斑马纹着色器'
        '(stripe=smoothstep(0.02,0.04,|mod(reflectX×10,0.2)-0.1|))可视化连续性断裂。'
        '本发明实现18参数到A级曲面的实时参数化生成，80×64网格(5184顶点、10240三角面)'
        '更新延迟低于20ms，为汽车造型设计提供高效数字化工具。'
    )

    pdf.ln(6)
    pdf.section_title('摘要附图')
    pdf.body_text('摘要附图为Fig.1，展示算法总览的6面板视图。')

    path = os.path.join(OUTPUT_DIR, 'patent_abstract.pdf')
    pdf.output(path)
    print(f'Saved: {path}')
    return path


# ============================================================
# Main
# ============================================================

if __name__ == '__main__':
    print('='*50)
    print('  Patent Application Document Generator')
    print('='*50)

    p1 = generate_request_form()
    p2 = generate_specification()
    p3 = generate_claims()
    p4 = generate_abstract()

    print(f'\n{"="*50}')
    print('  All patent documents generated:')
    print(f'  1. Request Form:     {p1}')
    print(f'  2. Specification:    {p2}')
    print(f'  3. Claims:           {p3}')
    print(f'  4. Abstract:         {p4}')
    print(f'  5. Figures:          {os.path.join(OUTPUT_DIR, "patent_figures.pdf")}')
    print(f'{"="*50}')
