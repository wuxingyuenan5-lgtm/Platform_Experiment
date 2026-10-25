"""Versioned representative equity baskets; independent from official industries.

Membership is a research selection, never an assertion of revenue exposure.
ETF/index references are excluded from stock statistics. Do not backtest a new
catalogue as though its membership had been known before effectiveFrom.
"""

CATALOG_VERSION = "equity-themes-2026-10-25-expanded"
CATALOG_EFFECTIVE_FROM = "2026-10-25"
CN_THEMES = (
    (
        "AI／数字科技",
        (
            ("芯片设计与制造", "688981 688256 688041 603986"),
            ("半导体设备与材料", "002371 688012 688019 300346"),
            ("光通信", "300308 300502 300394"),
            ("PCB与覆铜板", "002916 002463 600183"),
            ("服务器", "000977 603019 000938"),
            ("电源与散热", "002837 300499"),
            ("软件与应用", "688111 002230"),
            ("电信运营与数字基础设施", "600941 601728 600050"),
            ("终端与消费电子", "002475 002241 300433"),
        ),
    ),
    (
        "新能源",
        (
            ("光伏", "601012 688223 002459"),
            ("风电", "002202 601615"),
            ("动力电池与材料", "300750 300014 002460 002812 603659"),
            ("储能", "300274 300750 300014"),
            ("新能源车", "002594 300450"),
        ),
    ),
    (
        "机器人／高端制造",
        (
            ("机器人零部件", "002050 688017 601689"),
            ("工业机器人", "002747 300024"),
            ("工业自动化", "300124 603728"),
            ("机床", "601882 688305 300161"),
            ("汽车零部件与智能驾驶", "600660 603596 002920 601689"),
            ("工程机械", "600031 000425 000157"),
        ),
    ),
    (
        "军工／空天",
        (
            ("航空装备", "600760 600893 000768"),
            ("军工电子", "002179 000733"),
            ("卫星与航天", "600118 601698 600879"),
            ("直升机与低空装备", "600038 002985"),
        ),
    ),
    (
        "医药",
        (
            ("创新药", "600276 688235"),
            ("成熟制药", "600196 600436"),
            ("研发服务", "603259 300347"),
            ("医疗器械", "300760 688271 300595"),
            ("医疗服务", "300015 600763"),
        ),
    ),
    (
        "消费",
        (
            ("食品饮料", "600519 600887 000858"),
            ("家电", "000333 600690 000651"),
            ("旅游与免税", "601888 600754"),
            ("养殖", "002714 300498"),
        ),
    ),
    (
        "资源／材料",
        (
            ("工业金属", "603993 601600"),
            ("贵金属", "601899 600547"),
            ("稀土", "600111 000831"),
            ("煤炭", "601088 601225"),
            ("油气", "600028 601857 600938"),
            ("钢铁", "600019 000932"),
            ("化工", "600309 600426"),
        ),
    ),
    (
        "金融",
        (("银行", "600036 601166 601398"), ("券商", "600030 300059"), ("保险", "601318 601601")),
    ),
    (
        "电力／公用事业",
        (
            ("水电运营", "600900 600025"),
            ("核电运营", "601985 003816"),
            ("火电运营", "600011 600027"),
            ("绿电运营", "600905 001289"),
            ("环保与水务", "600008 601200 000967"),
            ("电网设备", "600406 600089 601179 002028"),
            ("发电设备", "601727 600875"),
        ),
    ),
    (
        "交通运输／全球贸易",
        (
            ("油运", "600026 601872 601975"),
            ("集运", "601919 601083"),
            ("干散货", "601872 600428"),
            ("港口", "600018 001872 601298"),
            ("航空与机场", "601111 600029 600115 600009"),
            ("物流与快递", "002352 600233 002120 603056"),
        ),
    ),
    (
        "地产／基建链",
        (
            ("地产开发", "600048 001979 600383"),
            ("建筑与基建", "601668 601390 601186 601800"),
            ("水泥与建材", "600585 000786 002271 601636"),
        ),
    ),
    (
        "农业／养殖",
        (
            ("生猪与禽养殖", "002714 300498 002299"),
            ("种业", "000998 600313"),
            ("饲料与农化", "002311 600486"),
        ),
    ),
    (
        "传媒／游戏",
        (
            ("游戏", "002555 002558 002624"),
            ("影视与出版", "300251 601098 601928"),
            ("广告", "002027"),
        ),
    ),
)
US_THEMES = (
    (
        "AI／数字科技",
        (
            ("芯片与制造", "NVDA AMD AVGO TSM MU"),
            ("设备", "AMAT LRCX KLAC"),
            ("网络与光通信", "ANET MRVL COHR LITE"),
            ("服务器与电子制造", "DELL HPE SMCI CLS TTMI"),
            ("电源与散热", "VRT"),
            ("云平台", "MSFT AMZN GOOGL ORCL"),
            ("软件与应用", "PLTR CRM NOW"),
            ("网络安全", "CRWD PANW FTNT"),
            ("数字平台与终端", "META AAPL"),
        ),
    ),
    (
        "工业／自动化",
        (
            ("工业自动化", "ROK EMR HON"),
            ("工程机械", "CAT URI"),
            ("电气设备", "ETN GEV"),
            ("工程建设", "PWR"),
        ),
    ),
    (
        "军工／航空航天",
        (
            ("国防装备", "LMT RTX NOC GD"),
            ("航空与发动机", "GE BA"),
            ("商业航天与卫星", "RKLB ASTS"),
        ),
    ),
    (
        "电力／电网／核能",
        (
            ("公用事业", "NEE SO DUK"),
            ("独立发电", "CEG VST"),
            ("电网设备与工程", "ETN GEV PWR"),
            ("核燃料与设备", "CCJ BWXT"),
            ("先进核能", "OKLO SMR"),
        ),
    ),
    (
        "医疗",
        (
            ("制药", "LLY JNJ ABBV MRK NVO"),
            ("生物科技", "REGN VRTX AMGN"),
            ("医疗器械", "ISRG ABT BSX"),
            ("医疗服务", "UNH HCA"),
        ),
    ),
    (
        "消费",
        (
            ("必选消费", "PG KO PEP"),
            ("零售", "COST WMT"),
            ("可选消费", "AMZN TSLA NKE"),
            ("旅游与酒店", "BKNG MAR"),
        ),
    ),
    (
        "金融",
        (
            ("银行", "JPM BAC C"),
            ("区域银行", "PNC USB"),
            ("保险", "PGR CB"),
            ("资管", "BLK"),
            ("支付", "V MA"),
            ("金融科技", "HOOD COIN"),
        ),
    ),
    (
        "能源／资源／材料",
        (
            ("油气", "XOM CVX COP EOG"),
            ("油服", "SLB HAL"),
            ("金属矿业", "FCX SCCO NEM AEM"),
            ("化工材料", "LIN APD"),
        ),
    ),
    (
        "交通运输／全球贸易",
        (
            ("油运", "FRO STNG DHT HAFN"),
            ("集运", "ZIM MATX DAC"),
            ("干散货", "SBLK GNK SB"),
            ("铁路", "UNP CSX CNI CP"),
            ("航空", "DAL UAL LUV"),
            ("物流与卡车运输", "UPS FDX JBHT ODFL"),
        ),
    ),
    (
        "地产／住宅与基建",
        (
            ("住宅建设", "DHI LEN PHM"),
            ("仓储与住宅REIT", "PLD VMRK"),
            ("数据中心与通信REIT", "EQIX DLR AMT"),
            ("基建与建材", "PWR VMC MLM"),
        ),
    ),
    ("清洁能源", (("光伏与储能", "FSLR ENPH SEDG"), ("电池与新能源车", "ALB TSLA"))),
    ("传媒／娱乐", (("流媒体与内容", "NFLX DIS SPOT"), ("游戏", "TTWO RBLX"))),
)

SATELLITE_THEMES = {"cn": {"农业／养殖", "传媒／游戏"}, "us": {"清洁能源", "传媒／娱乐"}}


# (code, label, coverage, scope, official methodology/product link)
def _cn_ref(code, label, scope):
    return (
        code,
        label,
        "部分覆盖",
        scope,
        f"https://www.sse.com.cn/assortment/fund/list/etfinfo/basic/index.shtml?FUNDID={code}",
    )


CN_REFERENCES = {
    "AI／数字科技": [_cn_ref("588080", "科创50ETF", "科创板宽基，非AI专属")],
    "新能源": [_cn_ref("515790", "光伏ETF", "光伏产业")],
    "机器人／高端制造": [_cn_ref("562500", "机器人ETF", "中证机器人指数")],
    "军工／空天": [_cn_ref("512660", "军工ETF", "中证军工指数")],
    "医药": [_cn_ref("512010", "医药ETF", "沪深300医药卫生")],
    "消费": [_cn_ref("515170", "食品饮料ETF", "食品饮料")],
    "资源／材料": [_cn_ref("512400", "有色金属ETF", "有色金属")],
    "金融": [_cn_ref("510230", "金融ETF", "上证180金融")],
    "电力／公用事业": [
        (
            "159301",
            "公用事业ETF",
            "部分覆盖",
            "公用事业，不覆盖全部电力设备",
            "https://www.chinaamc.com.cn/fund/159301/index.shtml",
        )
    ],
    "交通运输／全球贸易": [_cn_ref("561320", "交运ETF", "综合交通运输，非纯油运")],
    "地产／基建链": [
        _cn_ref("512200", "地产ETF", "房地产"),
        _cn_ref("516950", "基建ETF", "基建工程"),
    ],
    "农业／养殖": [_cn_ref("512620", "农业ETF", "农业产业")],
    "传媒／游戏": [_cn_ref("512980", "传媒ETF", "传媒行业")],
    "红利／央国企": [
        _cn_ref("515180", "中证红利ETF", "红利筛选，非央企专属"),
        _cn_ref("512890", "红利低波ETF", "红利与低波"),
        (
            "560700",
            "央企股东回报ETF",
            "部分覆盖",
            "央企与股东回报交集，非全部国企",
            "https://www.gffunds.com.cn/funds/?fundcode=560700",
        ),
    ],
}

US_REFERENCES = {
    "交通运输／全球贸易": [
        (
            "IYT",
            "美国交通运输",
            "部分覆盖",
            "美国运输公司，非纯航运",
            "https://www.ishares.com/us/products/239501/ishares-u-s-transportation-etf",
        ),
        (
            "BOAT",
            "全球航运",
            "部分覆盖",
            "全球航运股票，含非美公司",
            "https://sonicshares.com/boat/",
        ),
        (
            "BWET",
            "油轮运费期货",
            "期货工具",
            "原油油轮运费期货，非航运股票或现货运价",
            "https://amplifyetfs.com/bwet/",
        ),
    ],
    "地产／住宅与基建": [
        (
            "XLRE",
            "房地产ETF",
            "部分覆盖",
            "标普500房地产，非住宅建筑全集",
            "https://www.sectorspdrs.com/mainfund/xlre",
        )
    ],
    "AI／数字科技": [
        (
            "QQQ",
            "纳指100",
            "宽泛参考",
            "纳斯达克上市非金融公司",
            "https://www.invesco.com/qqq-etf/en/about.html",
        ),
        (
            "SOXX",
            "半导体ETF",
            "部分覆盖",
            "美国上市半导体公司",
            "https://www.ishares.com/us/products/239705/",
        ),
    ],
    "工业／自动化": [
        ("XLI", "工业ETF", "部分覆盖", "标普500工业", "https://www.sectorspdrs.com/mainfund/xli")
    ],
    "军工／航空航天": [
        (
            "ITA",
            "航空航天与国防ETF",
            "部分覆盖",
            "美国航空航天与国防",
            "https://www.ishares.com/us/products/239502/",
        )
    ],
    "电力／电网／核能": [
        (
            "XLU",
            "公用事业ETF",
            "部分覆盖",
            "标普500公用事业",
            "https://www.sectorspdrs.com/mainfund/xlu",
        )
    ],
    "医疗": [
        ("XLV", "医疗ETF", "宽泛参考", "标普500医疗", "https://www.sectorspdrs.com/mainfund/xlv"),
        (
            "IBB",
            "生物科技ETF",
            "部分覆盖",
            "美国上市生物科技",
            "https://www.ishares.com/us/products/239699/",
        ),
    ],
    "消费": [
        (
            "XLY",
            "可选消费ETF",
            "部分覆盖",
            "标普500可选消费",
            "https://www.sectorspdrs.com/mainfund/xly",
        ),
        (
            "XLP",
            "必选消费ETF",
            "部分覆盖",
            "标普500必选消费",
            "https://www.sectorspdrs.com/mainfund/xlp",
        ),
    ],
    "金融": [
        ("XLF", "金融ETF", "宽泛参考", "标普500金融", "https://www.sectorspdrs.com/mainfund/xlf")
    ],
    "能源／资源／材料": [
        ("XLE", "能源ETF", "部分覆盖", "标普500能源", "https://www.sectorspdrs.com/mainfund/xle"),
        ("XLB", "材料ETF", "部分覆盖", "标普500材料", "https://www.sectorspdrs.com/mainfund/xlb"),
    ],
    "红利／价值／质量／低波": [
        (
            "SCHD",
            "红利",
            "风格参考",
            "美国股票",
            "https://www.schwabassetmanagement.com/products/schd",
        ),
        (
            "VTV",
            "价值",
            "风格参考",
            "美国大盘",
            "https://investor.vanguard.com/investment-products/etfs/profile/vtv",
        ),
        ("QUAL", "质量", "风格参考", "美国股票", "https://www.ishares.com/us/products/256101/"),
        ("USMV", "低波", "风格参考", "美国股票", "https://www.ishares.com/us/products/239695/"),
    ],
}
# Cross-links reuse the destination basket rather than copying its stocks.
RELATED_THEMES = {
    "cn": {
        "AI／数字科技": ["机器人／高端制造", "电力／公用事业"],
        "新能源": ["电力／公用事业", "资源／材料"],
    },
    "us": {
        "AI／数字科技": ["电力／电网／核能", "工业／自动化"],
        "工业／自动化": ["电力／电网／核能"],
    },
}
CN_THEME_CODES = tuple(
    sorted({s for _, parts in CN_THEMES for _, codes in parts for s in codes.split()})
)

CN_INDICES = {
    "000016": "上证50",
    "000300": "沪深300",
    "000905": "中证500",
    "000852": "中证1000",
    "000688": "科创50",
    "000922": "中证红利",
    "000510": "中证A500",
}

# Style proxies remain separate from thematic stock membership. Scope describes
# mixed exposures rather than treating every ETF as a pure long-short factor.
CN_STYLES = (
    ("159656", "成长", "沪深300成长", "https://www.wjasset.com/products/etf/159656/index.html"),
    ("510030", "价值", "上证180价值；与300成长的样本空间不同", _cn_ref("510030", "", "")[4]),
    ("563360", "大中盘", "中证A500", _cn_ref("563360", "", "")[4]),
    ("510500", "中盘", "中证500", _cn_ref("510500", "", "")[4]),
    ("563300", "小盘", "中证2000", _cn_ref("563300", "", "")[4]),
    (
        "159967",
        "动量成长",
        "创业板动量成长；混合成长、动量与板块暴露",
        "https://f.chinaamc.com/fund/159967/index.shtml",
    ),
    ("515910", "质量", "MSCI中国A股国际质量", _cn_ref("515910", "", "")[4]),
    ("512890", "红利低波", "红利与低波交集；非纯低波", _cn_ref("512890", "", "")[4]),
    ("515180", "红利", "中证红利；不等于无风险防守", _cn_ref("515180", "", "")[4]),
    (
        "560700",
        "央企股东回报",
        "所有制与股东回报交集",
        "https://www.gffunds.com.cn/funds/?fundcode=560700",
    ),
)
US_STYLES = (
    ("IWF", "成长", "Russell 1000 Growth", "https://www.ishares.com/us/products/etf-investments"),
    ("IWD", "价值", "Russell 1000 Value", "https://www.ishares.com/us/products/etf-investments"),
    (
        "SPY",
        "大盘",
        "标普500市值加权",
        "https://www.ssga.com/us/en/intermediary/etfs/spdr-sp-500-etf-trust-spy",
    ),
    ("IJH", "中盘", "标普MidCap 400", "https://www.ishares.com/us/products/etf-investments"),
    ("IWM", "小盘", "Russell 2000", "https://www.ishares.com/us/products/etf-investments"),
    (
        "RSP",
        "等权",
        "标普500等权；带有规模与再平衡暴露",
        "https://www.invesco.com/us/financial-products/etfs/product-detail?productId=RSP",
    ),
    ("MTUM", "动量", "美国股票动量筛选", "https://www.ishares.com/us/products/etf-investments"),
    ("QUAL", "质量", "盈利能力、杠杆与盈利稳定性", "https://www.ishares.com/us/products/256101/"),
    ("USMV", "低波", "美国最小波动组合", "https://www.ishares.com/us/products/239695/"),
    (
        "SCHD",
        "红利",
        "股息与质量筛选；混合风格",
        "https://www.schwabassetmanagement.com/products/schd",
    ),
    (
        "SPHB",
        "高贝塔",
        "标普500高Beta；非杠杆倍数",
        "https://www.invesco.com/us/financial-products/etfs/product-detail?productId=SPHB",
    ),
)
STYLE_PAIRS = {
    "cn": (
        ("成长／价值", "159656", "510030"),
        ("小盘／大中盘", "563300", "563360"),
        ("质量／大中盘", "515910", "563360"),
        ("红利／大中盘", "515180", "563360"),
        ("动量成长／大中盘", "159967", "563360"),
    ),
    "us": (
        ("成长／价值", "IWF", "IWD"),
        ("小盘／大盘", "IWM", "SPY"),
        ("等权／市值", "RSP", "SPY"),
        ("动量／大盘", "MTUM", "SPY"),
        ("质量／大盘", "QUAL", "SPY"),
        ("低波／高贝塔", "USMV", "SPHB"),
        ("红利／大盘", "SCHD", "SPY"),
    ),
}

US_EXTRA_SYMBOLS = tuple(
    sorted(
        {s for _, parts in US_THEMES for _, codes in parts for s in codes.split()}
        | {r[0] for rows in US_REFERENCES.values() for r in rows}
        | {r[0] for r in US_STYLES}
        | {"RSP", "IWM", "QQQ", "SPY", "^VIX", "^VIX3M"}
    )
)

CN_REFERENCE_CODES = tuple(
    sorted({r[0] for rows in CN_REFERENCES.values() for r in rows} | {r[0] for r in CN_STYLES})
)
