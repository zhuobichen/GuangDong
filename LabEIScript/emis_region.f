	PROGRAM  Emission Process 36km All
	
ccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc
c
c  Prepared by Wang Litao, Chen Dan and Zhang Qiang
c  DESE, Tsinghua University
c  All rights reserved
c
ccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc 
 
       
	IMPLICIT NONE

        INCLUDE 'GC_SPC3.EXT'
        INCLUDE 'PARMS3.EXT'
        INCLUDE 'FDESC3.EXT'
        INCLUDE 'IODECL3.EXT'

        include 'netcdf.inc'

        integer i,j,k,n,p,v,m,r
        integer*4 ncid, status, fid
        integer nlay, nsec, nrow, ncol
        PARAMETER     (nsec = 8)
        PARAMETER     (nlay = 1)
        PARAMETER     (nrow = 202)
        PARAMETER     (ncol = 268)
        real, allocatable :: Emis(:,:,:,:,:),RawData(:,:),Rawtz(:,:,:)
        real, allocatable :: Rawlay(:,:),Rawmn(:,:),Rawwe(:,:)
        real, allocatable :: Rawhr(:,:,:,:)
        real, allocatable :: final_emi(:,:,:,:)
        real, allocatable :: noxlig(:,:,:),RawData3d(:,:,:)
        real, allocatable :: biovoc(:,:,:,:)
        real, allocatable :: HCLd(:,:,:),CLd(:,:,:)
        real, allocatable :: RR(:,:)

        integer SJDATE, EJDATE,JDATE,JTIME

        character*4 yyear,mmonth,sstard,eend
        character(4) :: cmonth, ctmp
        integer year,month,startday,endday,startdayofweek,cday
        integer, allocatable :: RID(:,:)

        logical LOGDEV

        character*16 PNAME, FNAME, FNAME0
        character*500, in_file
        data PNAME / 'emis_region' /

        character*36, base
        data base /'/bigdata/emis-make/Chenmeijun/GD_D3/'/

        allocate (Emis(ncol,nrow,1,nsec,1))
        Emis = 0

        allocate (RawData(ncol,nrow))
        RawData = 0

        allocate (final_emi(1,1,ncol,nrow))
        final_emi = 0


        do v = 1, 8
        print*, "working on "// GC_SPC3(v)
        status=nf_open(base//"nclproject/regionfile"
     &  //"/regionfile_HZ.nc",nf_nowrite,ncid)
      if(status==nf_noerr) then
        status=nf_inq_varid(ncid,TRIM(GC_SPC3(v)),fid)
        if(status/=nf_noerr) call handle_nc_err(status)
        status=nf_get_var_real(ncid,fid,RawData(:,:))
        if(status/=nf_noerr) call handle_nc_err(status)
            do i=1,ncol
             do j=1,nrow
		Emis(i,j,1,v,1) = RawData(i,j) 
	     enddo
            enddo	
        status=nf_close(ncid)
        if(status/=nf_noerr) call handle_nc_err(status)
      else
        print*, TRIM(GC_SPC3(v)), "is not available"
      endif
      enddo

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

       SJDATE=0
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
       NLAYS3D=1
       NTHIK3D=1
       VGTYP3D=2
       VGTOP3D=10000
       TSTEP3D=000000
       SDATE3D=SJDATE
       STIME3D=000000


       NVARS3D = 8
 
       DO I = 1,8
       
         VNAME3D(I)=GC_SPC3(I)
         UNITS3D(I)='ratio'
         VDESC3D(I)='Emission for ' // GC_SPC3(I) // ''
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
	   
	FNAME="./regionfile"

      print*, "Emission file:", FNAME


	       IF ( .NOT. OPEN3( FNAME, FSNEW3, PNAME ) )
     $      CALL M3ERR( PNAME, SDATE3D, STIME3D,
     $      'Could not create '// FNAME // ' file',
     $      .TRUE. )
       write(*,*) 'open3============'  

         JDATE= SJDATE

!         DO J=1,1

         JTIME=STIME3D+(1-1)*10000


             DO I=1,8

             IF ( .NOT. WRITE3( FNAME, GC_SPC3(I),
     $         JDATE, JTIME, Emis(1,1,1,I,1) ) )
     $         CALL M3ERR( PNAME, JDATE, JTIME,
     $        'Could not write '// GC_SPC3(I) //'
     $         to ' // FNAME // ' file',
     $         .TRUE. )

           END DO
!         END DO

 

       IF ( .NOT. SHUT3() ) WRITE(LOGDEV,*)
     &     'Could not shut down ' // FNAME // ' file correctly'

      deallocate (Emis)
	end


        subroutine handle_nc_err(status)
                integer status
                write(*,*)'Netcdf Process Error!'
        end subroutine
