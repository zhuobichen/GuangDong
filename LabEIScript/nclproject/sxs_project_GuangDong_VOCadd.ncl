begin

system("rm -rf ./D3/GD2000/*/v42_2013voc.nc")

 SECS1=(/"canyinyouyan","cunchuyunshu","daolu","feidaolu","feiqiwuchuliD","feiqiwuchuliG","gudingD","gudingG","guochengD","guochengG","nongye","rongjishiyong","shengwuzhiD","shengwuzhiG","yangchen","edgar2015","canyinyouyan_new2","shitangyouyan_new"/)
    do sectors1=0,17
       SEC1=SECS1(sectors1)
       print("start..."+SEC1)
       ft=asciiread("VOC_TS_new.csv",(/18,24/),"float")
       ;system("rm ./D3/GD2000/"+SEC1+"/v42_2013voc.nc")
       fin=addfile("./D3/GD2000/"+SEC1+"/v42_2013.nc","r")
       fon=addfile("./D3/GD2000/"+SEC1+"/v42_2013voc.nc","c")
       var=fin->VOC

       fon->PAR    = var(:,:) * ft(sectors1,0)
       fon->OLE    = var(:,:) * ft(sectors1,1)
       fon->TOL    = var(:,:) * ft(sectors1,2)
       fon->XYLMN  = var(:,:) * ft(sectors1,3)
       fon->FORM   = var(:,:) * ft(sectors1,4)
       fon->ALD2   = var(:,:) * ft(sectors1,5)
       fon->ETH    = var(:,:) * ft(sectors1,6)
       fon->ISOP   = var(:,:) * ft(sectors1,7)
       fon->MEOH   = var(:,:) * ft(sectors1,8)
       fon->ETOH   = var(:,:) * ft(sectors1,9)
       fon->UNR    = var(:,:) * ft(sectors1,10)
       fon->CH4    = var(:,:) * ft(sectors1,11)
       fon->ETHA   = var(:,:) * ft(sectors1,12)
       fon->IOLE   = var(:,:) * ft(sectors1,13)
       fon->ALDX   = var(:,:) * ft(sectors1,14)
       fon->TERP   = var(:,:) * ft(sectors1,15)
       fon->PRPA   = var(:,:) * ft(sectors1,16)
       fon->BENZ   = var(:,:) * ft(sectors1,17)
       fon->ETHY   = var(:,:) * ft(sectors1,18)
       fon->ACET   = var(:,:) * ft(sectors1,19)
       fon->KET    = var(:,:) * ft(sectors1,20)
       fon->NAPH   = var(:,:) * ft(sectors1,21)
       fon->SOAALK = var(:,:) * ft(sectors1,22)
       fon->APIN   = var(:,:) * ft(sectors1,23)

       fon->NR     = var(:,:) * ft(sectors1,10)
       fon->XYL    = var(:,:) * ft(sectors1,3)
       fon->AACD   = var(:,:) * 0

       print("finish..."+SEC1)       
       delete(var)
       delete(fon)
       delete(fin)
       delete(ft)
       delete(SEC1)
    end do     

SECS2=(/"meicagriculture","meicindustry","meicpower","meicresidential","meictransportation"/)
    do sectors2=0,4
       SEC2=SECS2(sectors2)
       print("start..."+SEC2)
       ;system("rm ./D3/GD2000/"+SEC2+"/v42_2013voc.nc")
       system("cp ./D3/GD2000/"+SEC2+"/v42_2013.nc ./D3/GD2000/"+SEC2+"/v42_2013voc.nc")
       fin2=addfile("./D3/GD2000/"+SEC2+"/v42_2013.nc","r")
       fon2=addfile("./D3/GD2000/"+SEC2+"/v42_2013voc.nc","w")

       fon2->SOAALK = fin2->PAR(:,:) * 0.108
       fon2->XYLMN  = fin2->XYL(:,:) * 0.998
       fon2->NAPH   = fin2->XYL(:,:) * 0.002
       fon2->NR     = fin2->UNR(:,:) * 1.0

       print("finish..."+SEC2)       
       delete(fon2)
       delete(fin2)
       delete(SEC2)
    end do   

end

