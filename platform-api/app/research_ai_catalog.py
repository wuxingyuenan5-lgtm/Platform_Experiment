"""AI research coverage, not portfolio membership or pure-AI revenue attribution."""

COMPANIES = [
    ("MSFT", 789019, "Microsoft", "云与算力运营", "MICROSOFT"),
    ("AMZN", 1018724, "Amazon", "云与算力运营", "AMAZON"),
    ("GOOGL", 1652044, "Alphabet", "云与算力运营", "ALPHABET"),
    ("META", 1326801, "Meta", "云与算力运营", "META"),
    ("ORCL", 1341439, "Oracle", "云与算力运营", "ORACLE"),
    ("CRWV", 1769628, "CoreWeave", "云与算力运营", "COREWEAVE"),
    ("NVDA", 1045810, "NVIDIA", "芯片与存储", "NVIDIA"),
    ("AMD", 2488, "AMD", "芯片与存储", "ADVANCED MICRO"),
    ("AVGO", 1730168, "Broadcom", "芯片与存储", "BROADCOM"),
    ("MU", 723125, "Micron", "芯片与存储", "MICRON"),
    ("ANET", 1596532, "Arista Networks", "服务器与网络", "ARISTA"),
    ("DELL", 1571996, "Dell", "服务器与网络", "DELL"),
    ("HPE", 1645590, "Hewlett Packard Enterprise", "服务器与网络", "HEWLETT"),
    ("SMCI", 1375365, "Super Micro", "服务器与网络", "SUPER MICRO"),
    ("VRT", 1674101, "Vertiv", "电力散热与机房", "VERTIV"),
    ("ETN", 1551182, "Eaton", "电力散热与机房", "EATON"),
    ("GEV", 1996810, "GE Vernova", "电力散热与机房", "GE VERNOVA"),
    ("CEG", 1868275, "Constellation Energy", "电力散热与机房", "CONSTELLATION"),
    ("EQIX", 1101239, "Equinix", "电力散热与机房", "EQUINIX"),
    ("DLR", 1297996, "Digital Realty", "电力散热与机房", "DIGITAL REALTY"),
    ("PLTR", 1321655, "Palantir", "软件与数据", "PALANTIR"),
    ("NOW", 1373715, "ServiceNow", "软件与数据", "SERVICENOW"),
    ("CRM", 1108524, "Salesforce", "软件与数据", "SALESFORCE"),
    ("SNOW", 1640147, "Snowflake", "软件与数据", "SNOWFLAKE"),
    ("DDOG", 1561550, "Datadog", "软件与数据", "DATADOG"),
    ("ADBE", 796343, "Adobe", "软件与数据", "ADOBE"),
    ("CRWD", 1535527, "CrowdStrike", "安全", "CROWDSTRIKE"),
    ("PANW", 1327567, "Palo Alto Networks", "安全", "PALO ALTO"),
]

METRICS = {
    "revenue": (
        "营业收入",
        [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
            "SalesRevenueNet",
            "RevenueFromContractWithCustomerIncludingAssessedTax",
        ],
    ),
    "grossProfit": ("毛利润", ["GrossProfit"]),
    "operatingIncome": ("经营利润", ["OperatingIncomeLoss"]),
    "netIncome": ("净利润", ["NetIncomeLoss"]),
    "cfo": ("经营现金流", ["NetCashProvidedByUsedInOperatingActivities"]),
    "capex": (
        "现金资本开支 · 报表购建资产口径",
        ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"],
    ),
    "rd": ("研发费用", ["ResearchAndDevelopmentExpense"]),
    "sbc": ("股份薪酬", ["ShareBasedCompensation"]),
    "da": (
        "折旧与摊销",
        [
            "DepreciationDepletionAndAmortization",
            "DepreciationDepletionAndAmortizationPropertyPlantAndEquipment",
            "DepreciationAmortizationAndAccretionNet",
        ],
    ),
    "interest": (
        "利息费用",
        ["InterestExpense", "InterestAndDebtExpense", "InterestExpenseNonOperating"],
    ),
    "leasePrincipal": ("融资租赁本金偿付", ["FinanceLeasePrincipalPayments"]),
    "leaseAdditions": (
        "融资租赁新增使用权资产 · 非现金",
        ["FinanceLeaseRightOfUseAssetObtainedInExchangeForFinanceLeaseLiability"],
    ),
    "debtIssued": ("发行长期债务所得", ["ProceedsFromIssuanceOfLongTermDebt"]),
}
INSTANT_METRICS = {
    "cash": ("现金及现金等价物", ["CashAndCashEquivalentsAtCarryingValue"]),
    "shortInvestments": ("短期投资", ["ShortTermInvestments"]),
    "debtCurrent": ("一年内到期长期债务", ["LongTermDebtCurrent"]),
    "debtNoncurrent": ("非流动长期债务", ["LongTermDebtNoncurrent", "LongTermDebt"]),
    "leaseLiability": ("融资租赁负债", ["FinanceLeaseLiability"]),
    "ppe": ("固定资产净额", ["PropertyPlantAndEquipmentNet"]),
    "rpo": ("剩余履约义务 · RPO", ["RevenueRemainingPerformanceObligation"]),
    "receivables": ("应收账款净额", ["AccountsReceivableNetCurrent"]),
    "inventory": ("存货净额", ["InventoryNet"]),
}
