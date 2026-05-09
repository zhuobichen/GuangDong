begin

 SECS1=(/"canyinyouyan","cunchuyunshu","daolu","feidaolu","feiqiwuchuliD","feiqiwuchuliG","gudingD","gudingG","guochengD","guochengG","nongye","rongjishiyong","shengwuzhiD","shengwuzhiG","yangchen","meicagriculture","meicindustry","meicpower","meicresidential","meictransportation","edgar2015","canyinyouyan_new2","shitangyouyan_new"/)
    do sectors1=0,22
       SEC1=SECS1(sectors1)
       print("start..."+SEC1)
       ft=asciiread("PM25_TS_new.csv",(/23,18/),"float")
       system("rm ./D3/GD2000/"+SEC1+"/v42_2013pm.nc")
       fin=addfile("./D3/GD2000/"+SEC1+"/v42_2013.nc","r")
       fon=addfile("./D3/GD2000/"+SEC1+"/v42_2013pm.nc","c")
       var=fin->PM25(:,:)

       fon->PEC    = var * ft(sectors1,0)
       fon->PNO3   = var * ft(sectors1,1)
       fon->POC    = var * ft(sectors1,2)
       fon->PSO4   = var * ft(sectors1,3)  
       fon->PCL    = var * ft(sectors1,4)
       fon->PNH4   = var * ft(sectors1,5)
       fon->PNA    = var * ft(sectors1,6)
       fon->PMG    = var * ft(sectors1,7)
       fon->PK     = var * ft(sectors1,8)
       fon->PCA    = var * ft(sectors1,9)
       fon->PNCOM  = var * ft(sectors1,10)
       fon->PFE    = var * ft(sectors1,11)
       fon->PAL    = var * ft(sectors1,12)
       fon->PSI    = var * ft(sectors1,13)
       fon->PTI    = var * ft(sectors1,14)
       fon->PMN    = var * ft(sectors1,15)
       fon->PH2O   = var * ft(sectors1,16)
       fon->PMOTHR = var * ft(sectors1,17)

       print("finish..."+SEC1)       
       delete(var)
       delete(fon)
       delete(fin)
       delete(ft)
       delete(SEC1)
    end do     

end
