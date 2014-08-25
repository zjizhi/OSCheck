#/bin/sh

rm -f fail.log

for ((i=8;i<144;i++))
do
{
	echo 'host',$i
	result=$(ipmitool -l lanplus -H 10.0.0.$i -U admin -P admin chassis power status)
 
	if [ ${result:0:7} = "Chassis" ];then
		echo 'ok'
	else
		echo $i >> fail.log
	fi
}
#& #if you want to execute in multi-thread mode,remove the sign '#' in front of the sign '&'

wait
done
