[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
#Powershell version of TLS generator. 
while ($true) {
$progressPreference = 'silentlyContinue'
#Grab EICAR first as binary then as text
invoke-webrequest -Uri https://secure.eicar.org/eicar.com -OutFile $NULL | Out-Null
start-sleep -seconds 5
#TLS version of TestmyIDS.com
invoke-webrequest -Uri https://evebox.org/files/testmyids.com -OutFile $NULL | Out-Null
start-sleep -seconds 5
#Download Google Homepage via TLS
invoke-webrequest -Uri https://www.google.com  -OutFile $NULL | Out-Null
start-sleep -seconds 5
#Download ESPN Homepage via TLS
invoke-webrequest -Uri https://www.espn.com -OutFile $NULL | Out-Null
start-sleep -seconds 5
}
