begin
        nlon    = 121
        nlat    = 133
        lon     = fspan(70,150,nlon)
        lon!0   = "lon"
        lon@long_name   = "longitude"
        lon@units       = "degrees_east"
        lat     = fspan(-11,55,nlat)
        lat!0   = "lat"
        lat@long_name   = "latitude"
        lat@units       = "degrees_north"

        reoc	= 0.6666667/2
	reor	= 0.5/2
        data    = new((/nlat,nlon/),"float")

do r = 0, nlat -1
print("working on line :"+r)
        data(r,:)       = gc_qarea((/lat(r)-reor,lat(r)-reor,lat(r)+reor,lat(r)+reor/),(/lon(0)-reoc,lon(0)+reoc,lon(0)-reoc,lon(0)+reoc/)) * 6371 ^ 2
end do
        data@_FillValue = -9999
        data!0  = "lat"
        data!1  = "lon"
        data&lat        = lat
        data&lon        = lon
        data@long_name  = "AREA km^2/0.5*0.667degree"

        fon     = "areacalc.nc"
        system("rm -f "+fon)
        fo      = addfile(fon,"c")
        fo->area        = data
        fo@history      = "Jia Xing, Dec.2009"
end
