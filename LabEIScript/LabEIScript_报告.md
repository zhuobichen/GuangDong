# LabEIScript 项目详细报告

## 项目概述

LabEIScript 是一个用于处理大气污染物排放数据的项目，主要用于生成 CMAQ（Community Multiscale Air Quality）模型所需的排放清单文件。该项目由清华大学环境学院王立涛、陈丹和张强开发。

## 主要功能

1. **大气污染物排放清单处理**
   - 处理多种污染物的排放数据
   - 生成符合 CMAQ 模型输入格式的排放文件
   - 支持不同来源的排放数据（自然源、人为源等）

2. **时空分配**
   - 月度时间分配
   - 周时间分配
   - 小时时间分配
   - 垂直分层分配

3. **多源排放数据融合**
   - MEIC 排放清单
   - EDGAR 排放数据
   - 本地化排放源
   - 海洋排放源

## 文件结构及说明

### 核心程序文件

#### 1. emis_cb6ae7.f
- **描述**：主要的大气污染物排放处理程序
- **功能**：
  - 处理 23 个排放部门的排放数据
  - 支持 CB6ae7 机制，包含 51 种化学物种
  - 输出格式为 Models-3 I/O API 兼容的 NetCDF 文件
- **处理的污染物**：
  - 气体污染物：CO、NO、NO2、NH3、SO2
  - NMVOCs（32种）：PAR、OLE、TOL、XYLMN、FORM、ALD2、ETH、ISOP、MEOH、ETOH、NR、ETHA、IOLE、ALDX、TERP、PRPA、BENZ、ETHY、ACET、KET、NAPH、SOAALK、APIN、UNR、XYL、AACD
  - 颗粒物：PMC、PEC、POC、PNO3、PSO4、PCL、PNH4、PNA、PMG、PK、PCA、PNCOM、PFE、PAL、PSI、PTI、PMN、PH2O、PMOTHR
- **排放部门**：
  1. 餐饮油烟 (canyinyouyan)
  2. 储存运输 (cunchuyunshu)
  3. 道路 (daolu)
  4. 非道路 (feidaolu)
  5. 非生物质燃烧D (feiqiwuchuliD)
  6. 非生物质燃烧G (feiqiwuchuliG)
  7. 固定源D (gudingD)
  8. 固定源G (gudingG)
  9. 工业过程D (guochengD)
  10. 工业过程G (guochengG)
  11. 农业 (nongye)
  12. 溶剂使用 (rongjishiyong)
  13. 生物质燃烧D (shengwuzhiD)
  14. 生物质燃烧G (shengwuzhiG)
  15. 扬尘 (yangchen)
  16. MEIC农业排放 (meicagriculture)
  17. MEIC工业排放 (meicindustry)
  18. MEIC电力排放 (meicpower)
  19. MEIC居民排放 (meicresidential)
  20. MEIC交通排放 (meictransportation)
  21. EDGAR2015 (edgar2015)
  22. 新餐饮油烟 (canyinyouyan_new2)
  23. 食堂油烟 (shitangyouyan_new)

#### 2. emis_ocean.f
- **描述**：海洋排放处理程序
- **功能**：
  - 处理海洋相关的排放数据
  - 支持 OPEN（开阔海域）和 SURF（表层海洋）两种类型
  - 输出海洋排放比例文件

#### 3. emis_region.f
- **描述**：区域排放处理程序
- **功能**：
  - 处理区域化的排放数据
  - 生成区域标识文件
  - 支持 GD（广东）和 FGD（粤港澳大湾区）区域

### 配置文件

#### 1. FDESC3.EXT
- **描述**：Models-3 I/O API 文件描述结构定义
- **内容**：定义了 Models-3 文件格式的数据结构和参数

#### 2. IODECL3.EXT
- **描述**：Models-3 I/O API 函数声明
- **内容**：包含了所有 I/O API 函数的声明和使用说明

#### 3. PARMS3.EXT
- **描述**：Models-3 I/O API 参数定义
- **内容**：定义了 I/O API 使用的各种参数和常量

#### 4. GC_SPC.EXT
- **描述**：CB6ae7 化学机制物种定义
- **内容**：定义了 51 种化学物种的名称和分子量

#### 5. GC_SPC2.EXT
- **描述**：海洋排放物种定义
- **内容**：定义了 OPEN 和 SURF 两种海洋排放类型

#### 6. GC_SPC3.EXT
- **描述**：区域标识定义
- **内容**：定义了 GD 和 FGD 两个区域标识

### 数据文件

#### 1. oceanfile
- **描述**：海洋排放数据文件（二进制格式）
- **用途**：存储海洋排放相关的网格数据

#### 2. temporal 目录
- **描述**：时间分配系数目录
- **内容**：
  - monthly：月度分配系数
  - weekly：周分配系数
  - hourly：小时分配系数
- **示例文件**：yangchen（月度分配系数示例）

#### 3. vertical 目录
- **描述**：垂直分层系数目录
- **内容**：各排放源的垂直分层分配系数

### NCL 脚本目录 (nclproject)

#### 1. sxs_project_GuangDong.ncl
- **描述**：广东省排放数据处理主脚本
- **功能**：将 shapefile 格式的排放数据转换为 NetCDF 格式

#### 2. sxs_project_GuangDong_PM25Add.ncl
- **描述**：PM2.5 数据添加脚本
- **功能**：处理额外的 PM2.5 排放数据

#### 3. sxs_project_GuangDong_VOCadd.ncl
- **描述**：VOC 数据添加脚本
- **功能**：处理额外的 VOC 排放数据

#### 4. sxs_project_MEIC.ncl
- **描述**：MEIC 数据处理脚本
- **功能**：处理 MEIC 排放清单数据

#### 5. PM25_TS_new.csv / VOC_TS_new.csv
- **描述**：时间序列数据文件
- **用途**：存储 PM2.5 和 VOC 的时间变化数据

### MEIC 目录

#### 1. GRIDCRO2D 文件
- **描述**：WRF 模型网格交叉参考文件
- **用途**：提供网格坐标信息

#### 2. NCL 脚本
- **描述**：MEIC 数据处理相关的 NCL 脚本
- **功能**：处理和导出 MEIC 排放数据

#### 3. CSV 文件
- **描述**：时间序列数据
- **用途**：存储 PM2.5 和 VOC 的时间变化特征

## 技术特点

1. **编程语言**：以 Fortran 为主，辅以 NCL（NCAR Command Language）
2. **数据格式**：NetCDF、Shapefile、CSV
3. **网格系统**： Lambert 投影，3km 分辨率
4. **时间分辨率**：小时级别
5. **垂直分层**：8 层 sigma 坐标

## 工作流程

1. **数据准备**
   - 收集各类排放源数据
   - 转换为标准格式

2. **空间分配**
   - 将排放数据分配到网格
   - 应用地图投影转换

3. **时间分配**
   - 应用月、周、小时变化系数
   - 生成时间序列排放数据

4. **垂直分配**
   - 根据排放源特征进行垂直分层
   - 生成多层排放数据

5. **化学物种分配**
   - 将排放量分配到不同化学物种
   - 应用化学机制转换

6. **输出生成**
   - 生成 Models-3 格式的排放文件
   - 生成配套的元数据文件

## 应用场景

1. **空气质量模拟**：为 CMAQ 模型提供排放输入
2. **政策评估**：评估不同减排政策的效果
3. **科学研究**：大气化学和传输研究
4. **环境影响评价**：建设项目的大气环境影响评估

## 注意事项

1. 该项目需要 Fortran 编译器和 NetCDF 库支持
2. NCL 脚本需要 NCAR Command Language 环境
3. 数据路径需要根据实际环境调整
4. 排放清单需要定期更新以保持时效性

## 开发团队

- **开发单位**：清华大学环境学院
- **主要开发者**：王立涛、陈丹、张强
- **版权声明**：保留所有权利

---
*报告生成时间：2025年12月12日*