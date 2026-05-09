begin

  year = 2000
  nrow = 202
  ncol = 268
  MONS=(/"00"/)
  do months=0,0
     MON=MONS(months)
     SECS=(/"agriculture","industry","power","residential","transportation"/)  
       do sectors=0,4
       SEC=SECS(sectors)
       data=new((/nrow*ncol,15/),double)
       data=0
       extract_data = new((/nrow*ncol/),string)
       extract_data = 0

       SPES=(/"ALD2","ALDX","ETH","ETHA","ETOH","FORM","IOLE","ISOP","MEOH","OLE","PAR","TERP","TOL","UNR","XYL"/)
          do species=0,14
          SPE=SPES(species)
          var=""+SPE+""
          indir	= "/bigdata/emis-make/hujiaqian/MEIC/DPEC_2000/"+MON+"/"+SEC+"/VOC"
          infile= systemfunc("ls "+indir+"/TS_"+SPE+".nc")
	  print(infile)

          fin = addfile(infile,"r")
          a = fin->$var$(:,:)
          a@_FillValue = 0

          grid_data=new((/nrow,ncol/),double)
          
          do i = 0,nrow-1
            do j = 0,ncol-1
            grid_data(i,j) = a(i,j)*366*24*3600 ;;mol/y
            end do
          end do

          do i = 0,nrow-1
            do j = 0,ncol-1
            data((i*ncol+j),species) = grid_data(i,j)
            end do
          end do
          data@_FillValue = 0

          delete(SPE)
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
        asciiwrite("DPEC_2000_"+MON+"_"+SEC+"_VOC.csv",extract_data)
        delete(SEC)
        delete(data)
        delete(extract_data)

       end do
  delete(MON)
  end do
        
end
