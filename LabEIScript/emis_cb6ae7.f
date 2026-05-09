	PROGRAM  Emission Process 36km All
	
ccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc
c
c  Prepared by Wang Litao, Chen Dan and Zhang Qiang
c  DESE, Tsinghua University
c  All rights reserved
c
ccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc 
 
       
	IMPLICIT NONE

        INCLUDE 'GC_SPC.EXT'
        INCLUDE 'PARMS3.EXT'
        INCLUDE 'FDESC3.EXT'
        INCLUDE 'IODECL3.EXT'

        include 'netcdf.inc'

        integer :: month_days(12)  ! 先声明数组
        DATA month_days /31,28,31,30,31,30,31,31,30,31,30,31/  ! 用DATA块初始化（Fortran 77兼容）
        integer :: days_before  ! 当月之前的总天数
        logical :: is_leap      ! 是否为闰

        integer i,j,k,n,p,v,m,r
        integer*4 ncid, status, fid
        integer nlay, nsec, nrow, ncol
        PARAMETER     (nsec = 23)
        PARAMETER     (nlay = 8)
        PARAMETER     (nrow = 202)
        PARAMETER     (ncol = 268)
        real, allocatable :: Emis(:,:,:,:,:),RawData(:,:),Rawtz(:,:,:)
        real, allocatable :: Rawlay(:,:),Rawmn(:,:),Rawwe(:,:)
        real, allocatable :: Rawhr(:,:)
        real, allocatable :: final_emi(:,:,:,:,:)
        real, allocatable :: noxlig(:,:,:),RawData3d(:,:,:)
        real, allocatable :: biovoc(:,:,:,:)
        real, allocatable :: HCLd(:,:,:),CLd(:,:,:)
        real, allocatable :: RR(:,:)

        integer SJDATE, EJDATE,JDATE,JTIME

        character*4 yyear,mmonth,sstard,eend,yr,sts,eds,SN
        character(4) :: cmonth, ctmp
        integer year,month,startday,endday,startdayofweek,cday,st,ed
        integer, allocatable :: RID(:,:)

        logical LOGDEV

        character*16 PNAME, FNAME, FNAME0
        character*500, in_file
        data PNAME / 'emis_cb6ae7' /

        character*39, base
        character*1, numtemp
        data base /'/bigdata/emis-make/hujiaqian/GD2023/D3/'/

        CHARACTER*46 SECNAME(nsec)

	DATA  SECNAME( 1) /'canyinyouyan                                 '/
	DATA  SECNAME( 2) /'cunchuyunshu                                 '/
	DATA  SECNAME( 3) /'daolu                                        '/
	DATA  SECNAME( 4) /'feidaolu                                     '/
	DATA  SECNAME( 5) /'feiqiwuchuliD                                '/
	DATA  SECNAME( 6) /'feiqiwuchuliG                                '/
	DATA  SECNAME( 7) /'gudingD                                      '/
	DATA  SECNAME( 8) /'gudingG                                      '/
	DATA  SECNAME( 9) /'guochengD                                    '/
	DATA  SECNAME(10) /'guochengG                                    '/
	DATA  SECNAME(11) /'nongye                                       '/
	DATA  SECNAME(12) /'rongjishiyong                                '/
	DATA  SECNAME(13) /'shengwuzhiD                                  '/
	DATA  SECNAME(14) /'shengwuzhiG                                  '/
	DATA  SECNAME(15) /'yangchen                                     '/
	DATA  SECNAME(16) /'meicagriculture                              '/
	DATA  SECNAME(17) /'meicindustry                                 '/
	DATA  SECNAME(18) /'meicpower                                    '/
	DATA  SECNAME(19) /'meicresidential                              '/
	DATA  SECNAME(20) /'meictransportation                           '/
	DATA  SECNAME(21) /'edgar2015                                    '/
	DATA  SECNAME(22) /'canyinyouyan_new2                            '/
	DATA  SECNAME(23) /'shitangyouyan_new                            '/

        yr = "2013"
        allocate (Emis(ncol,nrow,nlay,51,24))
        Emis = 0

        allocate (RawData(ncol,nrow))
        RawData = 0
        allocate (RawData3d(ncol,nrow,24))
        RawData3d = 0
        allocate (HCLd(ncol,nrow,24))
        HCLd = 0
        allocate (CLd(ncol,nrow,24))
        CLd = 0

        allocate (Rawlay(nsec,nlay))
        Rawlay = 0
        allocate (Rawmn(nsec,12))
        Rawmn = 0
        allocate (Rawwe(nsec,7))
        Rawwe = 0
        allocate (Rawhr(nsec,24))
        Rawhr = 0
        allocate (Rawtz(ncol,nrow,24))
        Rawtz = 0

!      allocate (noxlig(97,164,44))
!      noxlig = 0
!        allocate (biovoc(17,ncol,nrow,24))
!        biovoc = 0

!        allocate (RID(187,187))
!        RID = 0

!        allocate (RR(101,4))
!        RR = 0

        allocate (final_emi(nsec,ncol,nrow,nlay,51))
        final_emi = 0

! vertical layer
      do n = 1, nsec
      open (40+n, file= base//"vertical/"//TRIM(SECNAME(n)),
     &  form="formatted", status="old")
      read (40+n, *)  (Rawlay(n,k), k=1,nlay)
      close(40+n)
      enddo
      print*, Rawlay(1,:)
! monthly
      do n = 1, nsec
      open (40+n, file= base//"temporal/monthly/"//TRIM(SECNAME(n)),
     &  form="formatted", status="old")
      read (40+n, *)  (Rawmn(n,k), k=1,12)
      close(40+n)
      enddo
      print*, Rawmn(1,:)

! weekly
      do n = 1, nsec
      open (40+n, file= base//"temporal/weekly/"//TRIM(SECNAME(n)),
     &  form="formatted", status="old")
      read (40+n, *)  (Rawwe(n,k), k=1,7)
      close(40+n)
      enddo
      print*, Rawwe(1,:)

! hourly
      do n = 1, nsec
      open (40+n, file= base // "temporal/hourly/" // TRIM(SECNAME(n)),
     &  form="formatted", status="old")
      read (40+n, *)  (Rawhr(n,k), k=1,24)
      close(40+n)
      enddo
      print*, Rawhr(1,:)

        call getarg( 1, yyear)
        call getarg( 2, mmonth)
        call getarg( 3, sstard)
        call getarg( 4, eend)
        call getarg( 5, sts) ! start sector
        call getarg( 6, eds) ! end sector
        call getarg( 7, SN) ! get sector name
        read(yyear,*) year
        read(mmonth,*) month

        read(sstard,*) startday
        read(eend,*) endday
        read(sts,*) st
        read(eds,*) ed
         print*, mmonth, month
         cmonth = mmonth
         read(mmonth,'(a1)') ctmp
         print*, ctmp
         if(TRIM(ctmp).eq.'0') read(mmonth,'(2a1)') ctmp,cmonth
         print*, cmonth

! 4 Regional Ratio for post-2008

!      if (year.gt.2008) then
!      open (40, file= base // "calc/RR_" // TRIM(yyear),
!     &  form="formatted", status="old")
!      read (40, *)  ((RR(v,k), k=1,4),v=1,53)
!      close(40)
!      endif

! calc for CO
      do n = 1, nsec
       print*, "working on "// SECNAME(n) // GC_SPC(1)
	status=nf_open(base//"nclproject/D3/"//TRIM(SECNAME(n))
     &  //"/v42_"//yr//".nc",nf_nowrite,ncid)
      if(status==nf_noerr) then
        status=nf_inq_varid(ncid,'CO',fid)
        if(status/=nf_noerr) call handle_nc_err(status)
        status=nf_get_var_real(ncid,fid,RawData(:,:))
        if(status/=nf_noerr) call handle_nc_err(status)

        do k = 1,nlay
		final_emi(n,:,:,k,1) = RawData(:,:) * Rawlay(n,k) / GC_MOLWT(1)
        enddo

        status=nf_close(ncid)
        if(status/=nf_noerr) call handle_nc_err(status)
      else
        print*, TRIM(SECNAME(n)), "is not available for co"
      endif
      enddo
! calc for NOx
      do n = 1, nsec
       print*, "working on "// SECNAME(n) // " nox"
        status=nf_open(base//"nclproject/D3/"//TRIM(SECNAME(n))
     &  //"/v42_"//yr//".nc",nf_nowrite,ncid)
      if(status==nf_noerr) then
        status=nf_inq_varid(ncid,'NOX',fid)
        if(status/=nf_noerr) call handle_nc_err(status)
        status=nf_get_var_real(ncid,fid,RawData(:,:))
        if(status/=nf_noerr) call handle_nc_err(status)

        do k = 1,nlay
		final_emi(n,:,:,k,2) = RawData(:,:) * Rawlay(n,k) * 0.9 / GC_MOLWT(2)
		final_emi(n,:,:,k,3) = RawData(:,:) * Rawlay(n,k) * 0.1 / GC_MOLWT(3)
        enddo

        status=nf_close(ncid)
        if(status/=nf_noerr) call handle_nc_err(status)
      else
        print*, TRIM(SECNAME(n)), "is not available for nox"
      endif
      enddo
! calc for NH3
      do n = 1, nsec
       print*, "working on "// SECNAME(n) // GC_SPC(4)
        status=nf_open(base//"nclproject/D3/"//TRIM(SECNAME(n))
     &  //"/v42_"//yr//".nc",nf_nowrite,ncid)
      if(status==nf_noerr) then
        status=nf_inq_varid(ncid,'NH3',fid)
        if(status/=nf_noerr) call handle_nc_err(status)
        status=nf_get_var_real(ncid,fid,RawData(:,:))
        if(status/=nf_noerr) call handle_nc_err(status)

        do k = 1,nlay
		final_emi(n,:,:,k,4) = RawData(:,:) * Rawlay(n,k) / GC_MOLWT(4)
        enddo

        status=nf_close(ncid)
        if(status/=nf_noerr) call handle_nc_err(status)
      else
        print*, TRIM(SECNAME(n)), "is not available for nh3"
      endif
      enddo
! calc for SO2
      do n = 1, nsec
       print*, "working on "// SECNAME(n) // GC_SPC(5)
        status=nf_open(base//"nclproject/D3/"//TRIM(SECNAME(n))
     &  //"/v42_"//yr//".nc",nf_nowrite,ncid)
      if(status==nf_noerr) then
        status=nf_inq_varid(ncid,'SO2',fid)
        if(status/=nf_noerr) call handle_nc_err(status)
        status=nf_get_var_real(ncid,fid,RawData(:,:))
        if(status/=nf_noerr) call handle_nc_err(status)

        do k = 1,nlay
		final_emi(n,:,:,k,5) = RawData(:,:) * Rawlay(n,k) / GC_MOLWT(5)
        enddo

        status=nf_close(ncid)
        if(status/=nf_noerr) call handle_nc_err(status)
      else
        print*, TRIM(SECNAME(n)), "is not available for so2"
      endif
      enddo
! calc for SULF
      do n = 1, nsec
       print*, "working on "// SECNAME(n) // GC_SPC(6)
        status=nf_open(base//"nclproject/D3/"//TRIM(SECNAME(n))
     &  //"/v42_"//yr//".nc",nf_nowrite,ncid)
      if(status==nf_noerr) then
        status=nf_inq_varid(ncid,'SO2',fid)
        if(status/=nf_noerr) call handle_nc_err(status)
        status=nf_get_var_real(ncid,fid,RawData(:,:))
        if(status/=nf_noerr) call handle_nc_err(status)

        do k = 1,nlay
		final_emi(n,:,:,k,6) = RawData(:,:) * Rawlay(n,k) *0.02/ GC_MOLWT(6)
        enddo

        status=nf_close(ncid)
        if(status/=nf_noerr) call handle_nc_err(status)
      else
        print*, TRIM(SECNAME(n)), "is not available for sulf"
      endif
      enddo
! calc for CH4
!      do n = 1, nsec
!        print*, "working on "// SECNAME(n) // GC_SPC(7)
!        status=nf_open(base//"project/"//TRIM(SECNAME(n))
!     &  //"/ch4/v42_"//yyear//".nc",nf_nowrite,ncid)
!      if(status==nf_noerr) then
!        status=nf_inq_varid(ncid,'emi_ch4',fid)
!        if(status/=nf_noerr) call handle_nc_err(status)
!        status=nf_get_var_real(ncid,fid,RawData(:,:))
!        if(status/=nf_noerr) call handle_nc_err(status)

!        do k = 1,nlay
!		final_emi(n,:,:,k,7) = RawData(:,:) * Rawlay(n,k) / GC_MOLWT(7)
!        enddo

!        status=nf_close(ncid)
!        if(status/=nf_noerr) call handle_nc_err(status)
!      else
!        print*, TRIM(SECNAME(n)), "is not available for ch4"
!      endif
!      enddo
! calc for NMVOCs
      do v = 7, 32
      do n = 1, nsec
       print*, "working on "// SECNAME(n) // GC_SPC(v)
        status=nf_open(base//"nclproject/D3/"//TRIM(SECNAME(n))
     &  //"/v42_"//yr//"voc.nc",nf_nowrite,ncid)
      if(status==nf_noerr) then
        status=nf_inq_varid(ncid,TRIM(GC_SPC(v)),fid)
        if(status/=nf_noerr) call handle_nc_err(status)
        status=nf_get_var_real(ncid,fid,RawData(:,:))
        if(status/=nf_noerr) call handle_nc_err(status)

        do k = 1,nlay
		final_emi(n,:,:,k,v) = RawData(:,:) * Rawlay(n,k) 
        enddo
        status=nf_close(ncid)
        if(status/=nf_noerr) call handle_nc_err(status)
      else
        print*, TRIM(SECNAME(n)), "is not available for ch4"
      endif
      enddo
      enddo

! calc for PMC
      do n = 1, nsec
       print*, "working on "// SECNAME(n) // " pm10"
        status=nf_open(base//"nclproject/D3/"//TRIM(SECNAME(n))
     &  //"/v42_"//yr//".nc",nf_nowrite,ncid)
      if(status==nf_noerr) then
        status=nf_inq_varid(ncid,'PM10',fid)
        if(status/=nf_noerr) call handle_nc_err(status)
        status=nf_get_var_real(ncid,fid,RawData(:,:))
        if(status/=nf_noerr) call handle_nc_err(status)

        do k = 1,nlay
           final_emi(n,:,:,k,33) = RawData(:,:) * Rawlay(n,k) 
        enddo

        status=nf_close(ncid)
        if(status/=nf_noerr) call handle_nc_err(status)
      else
        print*, TRIM(SECNAME(n)), "is not available for pm10"
      endif
      enddo
     
! calc for PMs
      do v = 34, 51
      do n = 1, nsec
       print*, "working on "// SECNAME(n) // GC_SPC(v)
        status=nf_open(base//"nclproject/D3/"//TRIM(SECNAME(n))
     &  //"/v42_"//yr//"pm.nc",nf_nowrite,ncid)
       if(status==nf_noerr) then
         status=nf_inq_varid(ncid,TRIM(GC_SPC(v)),fid)
         if(status/=nf_noerr) call handle_nc_err(status)
         status=nf_get_var_real(ncid,fid,RawData(:,:))
         if(status/=nf_noerr) call handle_nc_err(status)

         do k = 1,nlay
            final_emi(n,:,:,k,v) = RawData(:,:) * Rawlay(n,k) 
         enddo
      
         status=nf_close(ncid)
         if(status/=nf_noerr) call handle_nc_err(status)
       else
         print*, TRIM(SECNAME(n)), "is not available for " // GC_SPC(v)
       endif
       enddo
       enddo

! calc for Lightning NOx

!      status=nf_open(base//"../geia/Lightning/noxlig_"//TRIM(cmonth)//".nc", nf_nowrite,ncid)
!      if(status==nf_noerr) then
!        status=nf_inq_varid(ncid,'NOx',fid)
!        if(status/=nf_noerr) call handle_nc_err(status)
!        status=nf_get_var_real(ncid,fid,noxlig(:,:,:))
!        if(status/=nf_noerr) call handle_nc_err(status)
!        status=nf_close(ncid)
!        if(status/=nf_noerr) call handle_nc_err(status)
!      endif

! calc for Natural VOC

!     status=nf_open(base//"Natural/cb05/natural_"//TRIM(cmonth)
!     &  //".nc", nf_nowrite,ncid)
!      if(status==nf_noerr) then
!      do v = 7, 28
!        status=nf_inq_varid(ncid,TRIM(GC_SPC(v)),fid)
!        if(status/=nf_noerr) call handle_nc_err(status)
!        status=nf_get_var_real(ncid,fid,RawData3d(:,:,:))
!        if(status/=nf_noerr) call handle_nc_err(status)
!        biovoc(v-6,:,:,:) = RawData3d(:,:,:)
!      enddo
!      endif

! calc for HCL

!      status=nf_open(base//"../geia/CL/HCL_nh108.nc", nf_nowrite,ncid)
!      if(status==nf_noerr) then
!        status=nf_inq_varid(ncid,'HCL',fid)
!        if(status/=nf_noerr) call handle_nc_err(status)
!        status=nf_get_var_real(ncid,fid,HCLd(:,:,:))
!        if(status/=nf_noerr) call handle_nc_err(status)
!        status=nf_close(ncid)
!        if(status/=nf_noerr) call handle_nc_err(status)
!      endif

! calc for CL

!      status=nf_open(base//"../geia/CL/CL_nh108.nc", nf_nowrite,ncid)
!      if(status==nf_noerr) then
!        status=nf_inq_varid(ncid,'CL',fid)
!        if(status/=nf_noerr) call handle_nc_err(status)
!        status=nf_get_var_real(ncid,fid,CLd(:,:,:))
!        if(status/=nf_noerr) call handle_nc_err(status)
!        status=nf_close(ncid)
!        if(status/=nf_noerr) call handle_nc_err(status)
!      endif

! 3 regions ratio for post-2008

!       status=nf_open(base//"region/map_3regions.nc", nf_nowrite,ncid)
!       if(status==nf_noerr) then
!         status=nf_inq_varid(ncid,'CID',fid)
!         if(status/=nf_noerr) call handle_nc_err(status)
!         status=nf_get_var_real(ncid,fid,RID(:,:))
!         if(status/=nf_noerr) call handle_nc_err(status)
!         status=nf_close(ncid)
!         if(status/=nf_noerr) call handle_nc_err(status)
!       endif


      print*, "calculation finished!..."

      if(year==1989) startdayofweek=5
      if(year==1990) startdayofweek=6
      if(year==1991) startdayofweek=0
      if(year==1992) startdayofweek=1
      if(year==1993) startdayofweek=3
      if(year==1994) startdayofweek=4
      if(year==1995) startdayofweek=5
      if(year==1996) startdayofweek=6
      if(year==1997) startdayofweek=1
      if(year==1998) startdayofweek=2
      if(year==1999) startdayofweek=3
      if(year==2000) startdayofweek=4
      if(year==2001) startdayofweek=6
      if(year==2002) startdayofweek=0
      if(year==2003) startdayofweek=1
      if(year==2004) startdayofweek=2
      if(year==2005) startdayofweek=4
      if(year==2006) startdayofweek=5
      if(year==2007) startdayofweek=6
      if(year==2008) startdayofweek=0
      if(year==2009) startdayofweek=2
      if(year==2010) startdayofweek=3
      if(year==2011) startdayofweek=4
      if(year==2012) startdayofweek=5
      if(year==2013) startdayofweek=0
      if(year==2014) startdayofweek=1
      if(year==2015) startdayofweek=2
      if(year==2016) startdayofweek=3
      if(year==2017) startdayofweek=5
      if(year==2018) startdayofweek=6
      if(year==2019) startdayofweek=0
      if(year==2020) startdayofweek=1
      if(year==2021) startdayofweek=3
      if(year==2022) startdayofweek=4
      if(year==2023) startdayofweek=5
      if(year==2024) startdayofweek=6
      if(year==2025) startdayofweek=1
      if(year==2026) startdayofweek=2
      if(year==2027) startdayofweek=3
      if(year==2030) startdayofweek=2

      ! 2. 判断闰年（修正2月天数）
      is_leap = .false.
      !if (mod(year,4)==0 .and. (mod(year,100)/=0 .or. mod(year,400)==0)) then
      if ( (mod(year,4).EQ.0) .AND. 
     &    ( (mod(year,100).NE.0) .OR. (mod(year,400).EQ.0) ) ) then
        is_leap = .true.
        month_days(2) = 29  ! 闰年2月29天
      end if

      ! 3. 计算当月之前所有月份的总天数（如2月则累加1月的31天）
      days_before = 0
      if (month > 1) then
        do i=1, month-1
          days_before = days_before + month_days(i)
        end do
      end if

      do p=startday,endday

        Emis=0
        cday = mod(p+startdayofweek,7) + 1


      do i=1,ncol
         print*, "working on COL: ", i
         do j=1,nrow
            do n = st,ed
               do m = 1,24
   		Emis(i,j,1:nlay,:,m)=Emis(i,j,1:nlay,:,m)+
     &            final_emi(n,i,j,:,:)*
     &             Rawmn(n,month)*
     &              Rawwe(n,cday)*
     &               Rawhr(n,MOD((m+7),24)+1)
               enddo
            enddo
!            if( year.gt.2008 ) then
!              do v = 1, 101
!                Emis(i,j,:,v,:) = Emis(i,j,:,v,:) * RR(v,RID(i,j)) ;
!              enddo
!            endif
         enddo
      enddo
! Add nox lightning

!      do m = 1,24
!         Emis(:,:,:,2,m) = Emis(:,:,:,2,m) + noxlig(:,:,:) * 0.9
!         Emis(:,:,:,3,m) = Emis(:,:,:,3,m) + noxlig(:,:,:) * 0.1
!      enddo

! Add natural VOC
!      if( ed.eq.6 ) then
!      do v = 7, 28
!         Emis(:,:,1,v,:) =  Emis(:,:,1,v,:) + biovoc(v-6,:,:,:) 
!      enddo
!      endif
! Add HCL
!         Emis(:,:,1,28,:) = Emis(:,:,1,28,:) + HCLd(:,:,:)
! Add CL
!         Emis(:,:,1,53,:) = Emis(:,:,1,53,:) + CLd(:,:,:)*35.5


      !SJDATE=year*1000+p
      SJDATE = year * 1000 + (days_before + p)

c--------------------------NETCDF FORMAT-------------------------
       LOGDEV=INIT3()
       
       FTYPE3D=1
       UPNAM3D=PNAME
       GDNAM3D='SD_2013'
       GDTYP3D=2
       P_ALP3D=25
       P_BET3D=40
       P_GAM3D=112.000
       XCENT3D=112.000
       YCENT3D=30.000
c the lower left corner is at the Y-coordinate origin 
       XORIG3D=-265500.000
c introduce a 100m shift between emission and mm5 map
       YORIG3D=-1089000.000
       XCELL3D=3000
       YCELL3D=3000
       NCOLS3D=ncol
       NROWS3D=nrow
       NLAYS3D=nlay
       NTHIK3D=1
       VGTYP3D=2
       VGTOP3D=10000
       VGLVS3D(1)=1
       VGLVS3D(2)=0.995
       VGLVS3D(3)=0.990
       VGLVS3D(4)=0.980
       VGLVS3D(5)=0.960
       VGLVS3D(6)=0.940
       VGLVS3D(7)=0.910
       VGLVS3D(8)=0.860
       VGLVS3D(9)=0.800
!       VGLVS3D(10)=0.740
!       VGLVS3D(11)=0.650
!       VGLVS3D(12)=0.550
!       VGLVS3D(13)=0.400
!       VGLVS3D(14)=0.200
!       VGLVS3D(15)=0.000
       TSTEP3D=010000
       SDATE3D=SJDATE
       STIME3D=000000


       NVARS3D = 51
 
       DO I = 1,32
       
         VNAME3D(I)=GC_SPC(I)
         UNITS3D(I)='moles/s'
         VDESC3D(I)='Emission for ' // GC_SPC(I) // ''
         VTYPE3D(I)=M3REAL
       
       END DO

       DO I = 33,51

         VNAME3D(I)=GC_SPC(I)
         UNITS3D(I)='g/s'
         VDESC3D(I)='Emission for ' // GC_SPC(I) // ''
         VTYPE3D(I)=M3REAL  

       END DO 


      EJDATE=SJDATE+1

      if(EJDATE==1989366) EJDATE = 1990001
      if(EJDATE==1990366) EJDATE = 1991001
      if(EJDATE==1991366) EJDATE = 1992001
      if(EJDATE==1992367) EJDATE = 1993001
      if(EJDATE==1993366) EJDATE = 1994001
      if(EJDATE==1994366) EJDATE = 1995001
      if(EJDATE==1995366) EJDATE = 1996001
      if(EJDATE==1996367) EJDATE = 1997001
      if(EJDATE==1997366) EJDATE = 1998001
      if(EJDATE==1998366) EJDATE = 1999001
      if(EJDATE==1999366) EJDATE = 2000001
      if(EJDATE==2000367) EJDATE = 2001001
      if(EJDATE==2001366) EJDATE = 2002001
      if(EJDATE==2002366) EJDATE = 2003001
      if(EJDATE==2003366) EJDATE = 2004001
      if(EJDATE==2004367) EJDATE = 2005001
      if(EJDATE==2005366) EJDATE = 2006001
      if(EJDATE==2006366) EJDATE = 2007001
      if(EJDATE==2007366) EJDATE = 2008001
      if(EJDATE==2008367) EJDATE = 2009001
      if(EJDATE==2009366) EJDATE = 2010001
      if(EJDATE==2010366) EJDATE = 2011001
      if(EJDATE==2011366) EJDATE = 2012001
      if(EJDATE==2012367) EJDATE = 2013001
      if(EJDATE==2013366) EJDATE = 2014001
      if(EJDATE==2014366) EJDATE = 2015001
      if(EJDATE==2015366) EJDATE = 2016001
      if(EJDATE==2016367) EJDATE = 2017001
      if(EJDATE==2017366) EJDATE = 2018001
      if(EJDATE==2018366) EJDATE = 2019001
      if(EJDATE==2019366) EJDATE = 2020001
      if(EJDATE==2020367) EJDATE = 2021001
      if(EJDATE==2021366) EJDATE = 2022001
      if(EJDATE==2022366) EJDATE = 2023001
      if(EJDATE==2023366) EJDATE = 2024001
      if(EJDATE==2024367) EJDATE = 2025001
      if(EJDATE==2025366) EJDATE = 2026001
      if(EJDATE==2026366) EJDATE = 2027001
      if(EJDATE==2027366) EJDATE = 2028001

        write(FNAME0,*) SJDATE

      print*, "Emission for:", SJDATE
	   
	FNAME="./EM_"//TRIM(SN)//"_"//ADJUSTL(FNAME0)

      print*, "Emission file:", FNAME


	       IF ( .NOT. OPEN3( FNAME, FSNEW3, PNAME ) )
     $      CALL M3ERR( PNAME, SDATE3D, STIME3D,
     $      'Could not create '// FNAME // ' file',
     $      .TRUE. )
       write(*,*) 'open3============'  

         JDATE= SJDATE
 
         DO J=1,24
           
         JTIME=STIME3D+(J-1)*10000 
         
                                         
             DO I=1,51
         
             IF ( .NOT. WRITE3( FNAME, GC_SPC(I),
     $         JDATE, JTIME, Emis(1,1,1,I,J) ) ) 
     $         CALL M3ERR( PNAME, JDATE, JTIME,
     $        'Could not write '// GC_SPC(I) //'
     $         to ' // FNAME // ' file',
     $         .TRUE. )

           END DO
         END DO

         JDATE= EJDATE

         DO J=1,1

         JTIME=STIME3D+(J-1)*10000


             DO I=1,51

             IF ( .NOT. WRITE3( FNAME, GC_SPC(I),
     $         JDATE, JTIME, Emis(1,1,1,I,J) ) )
     $         CALL M3ERR( PNAME, JDATE, JTIME,
     $        'Could not write '// GC_SPC(I) //'
     $         to ' // FNAME // ' file',
     $         .TRUE. )

           END DO
         END DO

 

       IF ( .NOT. SHUT3() ) WRITE(LOGDEV,*)
     &     'Could not shut down ' // FNAME // ' file correctly'

       end do
      deallocate (Emis)
	end


        subroutine handle_nc_err(status)
                integer status
                write(*,*)'Netcdf Process Error!'
        end subroutine
