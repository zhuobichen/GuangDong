begin       

    year=2000
    row=202
    col=268
    SECS=(/"meicagriculture","meicindustry","meicpower","meicresidential","meictransportation"/)
    do sectors=0,4
       SEC=SECS(sectors)
       print("start..."+SEC)
       fin=addfile("./D3/GD2000/"+SEC+"/final_"+SEC+".shp","float")
       system("rm ./D3/GD2000/"+SEC+"/v42_2013.nc")
       fon=addfile("./D3/GD2000/"+SEC+"/v42_2013.nc","c")
       VARSES=(/"BC","CO","NH3","NOX","OC","PM25","SO2","PM10","ALD2","ALDX","ETH","ETHA","ETOH","FORM","IOLE","ISOP","MEOH","OLE","PAR","TERP","TOL","UNR","XYL","XYLMN","CH4","PRPA","BENZ","ETHY","ACET","KET","NAPH","SOAALK","APIN","NR","AACD"/)
       nvarses=dimsizes(VARSES)
       data=new((/nvarses,row,col/),float)
       do v=0, 7
          var=VARSES(v)
          spe=doubletofloat(fin->$var$  * 10^6 / (366*24*3600)) ;g/s
          do i=0,row-1
            do j=0,col-1
            data(v,i,j) = spe(i*col+j) 
            end do 
          end do
          print(var+":"+sum(data(v,:,:))*3600*24*366/10^6 +"unit:t/y")
          delete(spe)
          delete(var)
       end do
         
       do l=8, 22
          var2=VARSES(l)
          spe=doubletofloat(fin->$var2$ / (366*24*3600)) ;mol/s
          do i=0,row-1
            do j=0,col-1
            data(l,i,j) = spe(i*col+j) 
            end do 
          end do
          print(var2+":"+sum(data(l,:,:))*3600*24*366/10^6 +"unit:10^6mol/y")
          delete(spe)
          delete(var2)
       end do

       do h=23, 34
          var3=VARSES(h)
          do i=0,row-1
            do j=0,col-1
            data(h,i,j) = 0
            end do 
          end do
          print(var3+":"+sum(data(l,:,:))*3600*24*366/10^6 +"unit:10^6mol/y")
          delete(var3)
       end do

       do m=0, nvarses-1
          fon->$VARSES(m)$ = data(m,:,:)
       end do

       delete(fin)
       delete(fon)
       delete(nvarses)
       delete(data)
       print("finish..."+SEC)
       delete(SEC)
    end do

end
