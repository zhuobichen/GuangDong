begin

f = addfile("TS_2013pm.nc","r")
vars = getfilevarnames(f)
nv = dimsizes(vars)
data = new((/nv,120,180/),"float")
do v = 0, nv-1
data(v,:,:) = (/f->$vars(v)$/)
end do
out = dim_sum_n(data,(/0/)) - f->PMFINE
print(sum(out)*3600*24*365/10^6)

end
