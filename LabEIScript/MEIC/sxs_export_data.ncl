begin

  year = 2000
  nrow = 202
  ncol = 268
  ;MONS=(/"2016","201604","201607","201610"/)
  MONS=(/"00"/)
  do months=0,0
     MON=MONS(months)
     SECS=(/"agriculture","industry","power","residential","transportation"/)  
       do sectors=0,4
       SEC=SECS(sectors)
       data=new((/nrow*ncol,9/),double)
       data=0
       extract_data = new((/nrow*ncol/),string)
       extract_data = 0

       SPES=(/"BC","CO","NH3","NOx","OC","PM10","PM25","SO2","VOC"/)
       VARSES=(/"bc","co","nh3","nox","oc","pm10","pm25","so2","voc"/)
          do species=0,8
          SPE=SPES(species)
          VARSE=VARSES(species)
          var="emi_"+VARSE+""
          indir	= "/bigdata/emis-make/hujiaqian/MEIC/DPEC_2000/"+MON+"/"+SEC+"/"+SPE+""
          infile= systemfunc("ls "+indir+"/TS_2000.nc")
	  print(infile)

          fin = addfile(infile,"r")
          a = fin->$var$(:,:)
          a@_FillValue = 0

          grid_data=new((/nrow,ncol/),double)
          
          do i = 0,nrow-1
             do j = 0,ncol-1
             grid_data(i,j) = a(i,j) * 366*24*3600 / 10^6 ;;t/y
             end do
          end do

          do i = 0,nrow-1
            do j = 0,ncol-1
            data((i*ncol+j),species) = grid_data(i,j)
            end do
          end do
          data@_FillValue = 0

          delete(SPE)
          delete(VARSE)
          delete(var)
          delete(indir)
          delete(infile)
          delete(fin)
          delete(a)
          delete(grid_data)
          end do

        do l =0, nrow*ncol - 1
        extract_data(l) = str_concat(sprintf("%7.8f,",data(l,:)))
        end do
        asciiwrite("DPEC_2000_"+MON+"_"+SEC+".csv",extract_data)
        delete(SEC)
        delete(data)
        delete(extract_data)

       end do
  delete(MON)
  end do
        
end
