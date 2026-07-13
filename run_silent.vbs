On Error Resume Next
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
WshShell.Environment("Process").Remove("PYTHONHOME")
WshShell.Environment("Process").Remove("PYTHONPATH")
On Error GoTo 0

Sub LogV(s)
  On Error Resume Next
  Set lf = fso.OpenTextFile("D:\GitWork\MMY-SymLink\vbs_launch.log", 8, True)
  lf.WriteLine Now & " " & s
  lf.Close
End Sub

Function Q(s)
  Q = """" & s & """"
End Function

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
LogV "vbs start scriptDir=" & scriptDir

candidates = Array( _
  "C:\Users\EDY\.workbuddy\binaries\python\versions\3.13.12\pythonw.exe", _
  "C:\Users\EDY\AppData\Local\Programs\Python\Python314\pythonw.exe", _
  "pythonw" _
)

pyw = ""
For Each c In candidates
  On Error Resume Next
  testCmd = Q(c) & " -c " & Q("import sys")
  rc = WshShell.Run(testCmd, 0, True)
  en = Err.Number
  On Error GoTo 0
  LogV "test rc=" & rc & " err=" & en & " cmd=" & testCmd
  If en = 0 And rc = 0 Then
    pyw = c
    Exit For
  End If
Next

If pyw = "" Then
  MsgBox "未找到可用的 Python 解释器（pythonw），请先安装 Python。", vbExclamation, "MMY-SymLink"
  WScript.Quit 1
End If

LogV "selected pyw=" & pyw
pywScript = fso.BuildPath(scriptDir, "run_silent.pyw")
WshShell.CurrentDirectory = scriptDir
LogV "launch " & pyw & " " & pywScript
' bWaitOnReturn=True: 等 GUI 关闭才让 wscript 退出，否则子进程 pythonw 会被一起带走（表现为“毫无反应”）
WshShell.Run Q(pyw) & " " & Q(pywScript), 1, True
LogV "vbs done"
