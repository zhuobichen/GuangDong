begin       

    year=2013
    row=202
    col=268
    SECS=(/"canyinyouyan","cunchuyunshu","daolu","feidaolu","feiqiwuchuliD","feiqiwuchuliG","gudingD","gudingG","guochengD","guochengG","nongye","rongjishiyong","shengwuzhiD","shengwuzhiG","yangchen","edgar2015","canyinyouyan_new2","shitangyouyan_new"/)
    do sectors=0,17
       SEC=SECS(sectors)
       print("start..."+SEC)
       fin=addfile("./D3/GD2000/"+SEC+"/final_"+SEC+".shp","float")
       system("rm ./D3/GD2000/"+SEC+"/v42_2013.nc")
       fon=addfile("./D3/GD2000/"+SEC+"/v42_2013.nc","c")
       VARSES=(/"SO2","NOX","CO","NH3","PM10","PM25","BC","OC","VOC"/)
       nvarses=dimsizes(VARSES)
       data=new((/nvarses,row,col/),float)
       do v=0, nvarses-2
          var=VARSES(v)
          spe=doubletofloat(fin->$var$ * 10^6 / (366*24*3600)) ;g/s
          do i=0,row-1
             do j=0,col-1
             data(v,i,j) = spe(i*col+j) 
             end do 
          end do
          print(var+":"+sum(data(v,:,:))*3600*24*366/10^6+"unit:t/y")
          delete(spe)
          delete(var)
       end do

       do l=nvarses-1, nvarses-1
          var=VARSES(l)
          spe=doubletofloat(fin->$var$ / (366*24*3600)) ;t/s
          do i=0,row-1
             do j=0,col-1
             data(l,i,j) = spe(i*col+j)
             end do
          end do
          print(var+":"+sum(data(l,:,:))*3600*24*366+"unit:t/y")
          delete(spe)  
          delete(var)
       end do

       data(4,:,:)=data(4,:,:)-data(5,:,:)

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
