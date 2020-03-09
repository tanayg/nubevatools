[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
#Powershell version of TLS generator.
while ($true) {
$progressPreference = 'silentlyContinue'
#Grab EICAR first as binary then as text
invoke-webrequest -Uri https://secure.eicar.org/eicar.com -OutFile $NULL | Out-Null
start-sleep -seconds 25
#TLS version of TestmyIDS.com
invoke-webrequest -Uri https://nubevalabs.s3.amazonaws.com/testmyids.txt -OutFile $NULL | Out-Null
start-sleep -seconds 25
#Download Google Homepage via TLS
invoke-webrequest -Uri https://www.google.com  -OutFile $NULL | Out-Null
start-sleep -seconds 25
#Download ESPN Homepage via TLS
invoke-webrequest -Uri https://www.bbc.com -OutFile $NULL | Out-Null
start-sleep -seconds 25
}
