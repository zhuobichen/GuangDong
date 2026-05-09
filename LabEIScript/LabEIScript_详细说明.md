# LabEIScript 项目文件详细说明

## 一、程序文件（.f结尾的Fortran程序）

### 1. emis_cb6ae7.f - 主要排放处理程序
**功能**：这是最核心的程序，负责处理所有大气污染物的排放数据。

#### 详细计算和分配流程：

**第一步：读取分配系数（程序启动时）**
```fortran
! 1. 读取垂直分配系数（每个排放源在不同高度的分配比例）
do n = 1, nsec  ! 遍历23个排放源
    read vertical/SECNAME(n)  ! 读取8个高度的分配比例
    Rawlay(n,k)  ! 存储到数组

! 2. 读取月度分配系数（每月排放占总排放的比例）
do n = 1, nsec
    read temporal/monthly/SECNAME(n)  ! 读取12个月的分配比例
    Rawmn(n,k)  ! 存储到数组

! 3. 读取周分配系数（每天排放占周排放的比例）
do n = 1, nsec
    read temporal/weekly/SECNAME(n)  ! 读取7天的分配比例
    Rawwe(n,k)  ! 存储到数组

! 4. 读取小时分配系数（每小时排放占日排放的比例）
do n = 1, nsec
    read temporal/hourly/SECNAME(n)  ! 读取24小时的分配比例
    Rawhr(n,k)  ! 存储到数组
```

**第二步：读取各排放源的原始排放数据**
```fortran
! 对每个排放源(n)和每种污染物(v)
do v = 1, 51  ! 51种污染物
    do n = 1, nsec  ! 23个排放源
        ! 读取NetCDF文件中的年排放总量
        status = nf_open("nclproject/D3/SECNAME(n)/v42_2013.nc")
        ! 读取网格化的年排放数据
        status = nf_get_var_real(ncid, ' pollutant_name ', RawData)

        ! 分配到不同高度（8层）
        do k = 1, nlay
            final_emi(n,i,j,k,v) = RawData(i,j) * Rawlay(n,k) / molecular_weight
        enddo
```

**第三步：时间分配计算（每天的计算）**
```fortran
! 对每个网格点(i,j)、每个排放源(n)、每个小时(m)进行计算
Emis(i,j,k,v,m) = final_emi(n,i,j,k,v) *
                  Rawmn(n,month) *      ! 月度系数
                  Rawwe(n,weekday) *    ! 周系数
                  Rawhr(n,hour)         ! 小时系数
```

**具体分配方式**：

1. **月度分配示例**（以交通排放为例）：
   - Rawmn(交通,1月) = 0.8  （1月是平均的80%）
   - Rawmn(交通,7月) = 1.2  （7月是平均的120%，暑期出行多）

2. **周分配示例**（以交通排放为例）：
   - Rawwe(交通,周一) = 1.2  （工作日排放高）
   - Rawwe(交通,周六) = 0.7  （周末排放低）

3. **小时分配示例**（以交通排放为例）：
   - Rawhr(交通,8时) = 1.5  （早高峰）
   - Rawhr(交通,14时) = 0.8  （下午平峰）
   - Rawhr(交通,18时) = 1.8  （晚高峰）
   - Rawhr(交通,3时) = 0.3  （凌晨低峰）

4. **垂直分配示例**：
   - 扬尘源：100%在第1层（地面）
   - 高烟囱工业源：5%在第1层，15%在第2层，...，10%在第8层

**特殊处理**：

1. **NOx的化学分配**：
   ```fortran
   final_emi(n,:,:,k,2) = RawData * Rawlay(n,k) * 0.9  ! 90%作为NO
   final_emi(n,:,:,k,3) = RawData * Rawlay(n,k) * 0.1  ! 10%作为NO2
   ```

2. **硫酸盐生成**：
   ```fortran
   final_emi(n,:,:,k,6) = SO2排放量 * Rawlay(n,k) * 0.02  ! 2%的SO2转化为硫酸盐
   ```

**输入参数**：
- yyear: 年份（如2013）
- mmonth: 月份（如01-12）
- sstard/eend: 开始和结束日期
- sts/eds: 开始和结束的排放源编号
- SN: 输出文件名称前缀

**输出结果**：
- 生成格式为 Models-3 的 NetCDF 文件
- 文件名：EM_SectorName_YYYYDDD（如EM_canyinyouyan_2013001）
- 包含51种污染物、8层高度、24小时的排放数据

### 2. emis_ocean.f - 海洋排放处理程序
**功能**：专门处理海洋相关的排放数据

**程序做的事情**：
- 处理两种海洋排放：开阔海域(OPEN)和表层海洋(SURF)
- 生成海洋排放比例文件
- 用于区分陆源和海源的排放

### 3. emis_region.f - 区域标识程序
**功能**：生成区域划分的标识文件

**程序做的事情**：
- 创建GD（广东）和FGD（粤港澳大湾区）两个区域的标识
- 用于模型识别不同区域的排放特征

---

## 二、配置文件（.EXT结尾）

### 1. GC_SPC.EXT - 化学物质定义文件
```fortran
        INTEGER        N_GC_SPC
        PARAMETER     (N_GC_SPC = 51)  ! 定义总共有51种化学物质
        CHARACTER*16   GC_SPC(N_GC_SPCD)  ! 存储化学物质名称
        REAL           GC_MOLWT(N_GC_SPCD) ! 存储分子量

	DATA  GC_SPC(  1), GC_MOLWT(  1) / 'CO              ', 28.0 /
	DATA  GC_SPC(  2), GC_MOLWT(  2) / 'NO              ', 30.0 /
	DATA  GC_SPC(  3), GC_MOLWT(  3) / 'NO2             ', 46.0 /
```
**作用**：
- 定义了空气中有哪些污染物（共51种）
- 包括每种污染物的名称和分子量
- 像是一本"污染物字典"

**包含的污染物类型**：
- 气体：一氧化碳(CO)、氮氧化物(NO/NO2)、二氧化硫(SO2)、氨气(NH3)
- 有机物：甲醛、乙醇、苯等32种挥发性有机物
- 颗粒物：PM2.5的各个组分（硫酸盐、硝酸盐、铵盐等）

### 2. GC_SPC2.EXT - 海洋排放类型定义
```fortran
        INTEGER        N_GC_SPC
        PARAMETER     (N_GC_SPC = 2)  ! 定义2种海洋排放类型
        CHARACTER*16   GC_SPC2(N_GC_SPCD)

	DATA  GC_SPC2(  1), GC_MOLWT(  1) / 'OPEN              ', 1.0 /
	DATA  GC_SPC2(  2), GC_MOLWT(  2) / 'SURF              ', 1.0 /
```
**作用**：
- 定义了两种海洋排放类型
- OPEN：开阔海域的排放
- SURF：近海表层的排放

### 3. GC_SPC3.EXT - 区域标识定义
```fortran
        INTEGER        N_GC_SPC
        PARAMETER     (N_GC_SPC = 2)  ! 定义2个区域
        CHARACTER*16   GC_SPC2(N_GC_SPCD)

	DATA  GC_SPC2(  1), GC_MOLWT(  1) / 'GD               ', 1.0 /
	DATA  GC_SPC2(  2), GC_MOLWT(  2) / 'FGD              ', 1.0 /
```
**作用**：
- GD：广东省区域
- FGD：粤港澳大湾区区域

### 4. PARMS3.EXT - 系统参数定义
```fortran
        INTEGER         MXDLEN3   !  描述文字的最大长度(80个字符)
        INTEGER         NAMLEN3   !  名称的最大长度(16个字符)
        INTEGER         MXFILE3   !  最多能打开的文件数量
        INTEGER         MXVARS3   !  每个文件最多包含的变量数量
```
**作用**：
- 定义了系统的基本参数和限制
- 比如文件名最多多长、一个文件最多能包含多少种污染物等
- 类似于系统的"配置参数"

### 5. FDESC3.EXT - 文件格式定义
```fortran
        INTEGER      FTYPE3D      ! 文件类型
        INTEGER      SDATE3D      ! 开始日期
        INTEGER      STIME3D      ! 开始时间
        INTEGER      NCOLS3D      ! 网格列数
        INTEGER      NROWS3D      ! 网格行数
        INTEGER      NLAYS3D      ! 垂直层数
        REAL*8       XORIG3D      ! X坐标起点
        REAL*8       YORIG3D      ! Y坐标起点
        REAL*8       XCELL3D      ! X方向网格大小
        REAL*8       YCELL3D      ! Y方向网格大小
```
**作用**：
- 定义了数据文件的标准格式
- 包括网格信息（多大范围、多细的网格）
- 时间信息（数据的开始时间）
- 变量信息（包含哪些污染物）

### 6. IODECL3.EXT - 输入输出函数声明
```fortran
        LOGICAL         OPEN3   !  打开文件
        LOGICAL         READ3   !  读取数据
        LOGICAL         WRITE3  !  写入数据
        LOGICAL         CLOSE3  !  关闭文件
```
**作用**：
- 定义了所有读写数据的函数
- 相当于程序操作文件的"工具箱"

---

## 三、数据文件

### 1. oceanfile - 海洋排放数据文件
**格式**：二进制格式
**内容**：
- 包含每个网格点的海洋排放比例
- 文件较大（约434KB），因为覆盖了整个研究区域

### 2. yangchen - 扬尘垂直分配系数
```
1.00
0.00
0.00
...
```
**内容**：
- 定义扬尘排放在不同高度的分配比例
- 第1行：100%排放在第1层（地面）
- 其他层：0%（扬尘只在地面排放）

### 3. temporal/monthly/yangchen - 月度变化系数
```
1	1	1	1	1	1	1	1	1	1	1	1
```
**内容**：
- 12个数值分别代表1-12月的排放比例
- 这里的数值都是1，表示扬尘排放全年均匀分布

### 4. temporal/weekly/ 目录
**内容**：存储每周7天的排放变化系数
- 比如工作日和周末的交通排放会有不同

### 5. temporal/hourly/ 目录
**内容**：存储一天24小时的排放变化系数
- 比如早晚高峰的交通排放会更高

### 6. vertical/ 目录
**内容**：存储不同排放源的垂直分配系数
- 每个排放源都有对应的文件
- 定义了污染物在不同高度的分配比例

---

## 四、NCL脚本目录（nclproject）

### 1. sxs_project_GuangDong.ncl - 广东数据处理脚本
```ncl
    SECS=(/"canyinyouyan","cunchuyunshu","daolu","feidaolu",.../)
    VARSES=(/"SO2","NOX","CO","NH3","PM10","PM25","BC","OC","VOC"/)
```
**功能**：
- 将原始的shapefile格式数据转换为NetCDF格式
- 处理18个不同的排放源
- 包括9种主要污染物

### 2. sxs_project_GuangDong_PM25Add.ncl - PM2.5补充数据
**功能**：处理额外的PM2.5排放数据

### 3. sxs_project_GuangDong_VOCadd.ncl - VOC补充数据
**功能**：处理额外的挥发性有机物数据

### 4. PM25_TS_new.csv - PM2.5时间序列数据
**内容**：存储PM2.5排放的时间变化特征

### 5. VOC_TS_new.csv - VOC时间序列数据
**内容**：存储VOC排放的时间变化特征

---

## 五、MEIC目录

### 1. GRIDCRO2D_* - WRF模型网格文件
**作用**：
- 提供模型的地理网格信息
- 包括每个网格的经纬度、海拔等

### 2. PM25_TS.csv / VOC_TS.csv - 时间序列数据
**内容**：
- 不同行业的PM2.5和VOC排放时间变化
- 用于更精确地分配排放量

### 3. NCL脚本文件
- areacal_geos.ncl：计算网格面积
- calc.ncl：计算脚本
- sxs_export_data.ncl：导出数据脚本
- sxs_project.ncl：主处理脚本

---

## 六、工作流程简化说明

1. **数据准备**：收集各种排放源的原始数据（工厂排放、汽车尾气等）

2. **格式转换**：
   - 使用NCL脚本将shapefile转为NetCDF
   - 统一数据格式

3. **时空分配**：
   - 时间分配：根据月/周/小时系数分配排放量
   - 垂直分配：根据不同源的高度特征分配
   - 空间分配：分配到各个网格

4. **化学物种分配**：
   - 将总排放量分配到不同化学物质
   - 使用GC_SPC.EXT定义的51种物质

5. **生成最终文件**：
   - 输出为Models-3标准格式
   - 可直接用于空气质量模型

这个项目的核心就是：把各种来源、各种格式的排放数据，经过处理，变成空气质量模型能够识别的标准格式文件。