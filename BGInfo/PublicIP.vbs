Dim o
Set o = CreateObject("MSXML2.XMLHTTP")
o.open "GET", "https://api.ipify.org", False
o.send
echo o.responseText