begin

  year = 2000
  ;MONS=(/"201601","201607","201610","201604"/)
  MONS=(/"00"/)
  do months=0,0
     MON=MONS(months)
     SECS=(/"agriculture","industry","power","residential","transportation"/)  
       do sectors=0,4
       SEC=SECS(sectors)
       SPES=(/"ALD2","ALDX","ETH","ETHA","ETOH","FORM","IOLE","ISOP","MEOH","OLE","PAR","TERP","TOL","UNR","XYL"/)
          do species=0,14
          SPE=SPES(species)
          var=""+SPE+""
          indir	= "/bigdata/emis-make/hujiaqian/MEIC/DPEC_2000/"+MON+"/"+SEC+"/VOC"
          infile= systemfunc("ls "+indir+"/2000*_"+SPE+".nc")
	  print(infile)

          fin = addfile(infile,"r")
          system("rm "+indir+"/TS_"+SPE+".nc")
          fon = addfile(""+indir+"/TS_"+SPE+".nc","c")

          a = fin->z(:)
          farea = addfile("./GRIDCRO2D_2060172","r")

          lon2d   = farea->LON(0,0,:,:)
          lat2d   = farea->LAT(0,0,:,:)

          nrow = 200
          ncol = 320
          lon     = fspan(70.0,149.75,ncol)
          lon!0   = "lon"
          lat     = fspan(10.0,59.75,nrow)
          lat!0   = "lat"
          reoc	= 0.25/2
	  reor	= 0.25/2
          area_wgt  = new((/nrow,ncol/),"float")
             do r = 0, nrow -1
             ;print("working on line :"+r)
             area_wgt(r,:) = gc_qarea((/lat(r)-reor,lat(r)-reor,lat(r)+reor,lat(r)+reor/),(/lon(0)-reoc,lon(0)+reoc,lon(0)-reoc,lon(0)+reoc/)) * 6371.22e3 ^ 2
             end do
        
          emi = new((/nrow,ncol/),double)
          a@_FillValue = -9999
             do i = 0,nrow-1
               do j = 0,ncol-1
               emi(nrow-1-i,j) = a(i*ncol+j)/area_wgt(nrow-1-i,j)
               end do
             end do

          emi@_FillValue = -9999
          emi@name = "$var$"
          emi!0  = "lat"
          emi!1  = "lon"
          emi&lat = (/lat/)
          emi&lon = (/lon/)  
          tmp2    = rgrid2rcm(emi&lat,emi&lon,emi,lat2d,lon2d,0)
          tmp2@_FillValue = 0
        
          newx    = tmp2 / (366*24*3600) / farea->MSFX2(0,0,:,:) * 3^2 * 10^6 * 10^6 ; mol/s
         
          newx!0  = "lat"
          newx!1  = "lon"
          newx@_FillValue = 0
          fon->$var$   = newx(:,:)
          delete(SPE)
          delete(var)
          delete(indir)
          delete(infile)
          delete(fin)
          delete(a)
          delete(emi)
          delete(tmp2)
          delete(newx)
          end do
       delete(SEC)
       end do
  delete(MON)
  end do
        
end

