 Firewall Blocker – Application Internet Access Manager
A lightweight, standalone Windows utility that blocks internet access for selected applications by creating firewall rules for all .exe files inside chosen folders and their subdirectories. Built with C++ and Win32 API – no external dependencies, no .NET, no installation required.

Personal use case: I created this tool to block internet access for SOLIDWORKS and CATIA to prevent license validation pop-ups and unwanted automatic updates, but it works for any Windows application.

📌 Overview
Feature	Description
Portable	Single .exe file – no installation, no registry changes
Batch processing	Add entire folders; all .exe files inside (including subfolders) are blocked at once
Protocol selection	Choose from TCP, UDP, ICMPv4, ICMPv6, GRE, IGMP, ESP, AH per path
Checkbox interface	Enable/disable blocking per folder with a single click
Complete reversal	One‑click “Restore All” removes every rule created by the tool
Customisable look	Dark theme with teal buttons and orange text (optional)
🚀 How It Works
Add a folder – Type or browse to an application’s installation directory.

Choose a protocol – Select the network protocol you want to block (TCP is usually sufficient).

Add to list – The folder appears in the list with its assigned protocol.

Check/uncheck – Tick the box next to each folder to decide which ones to block.

Click “Block Selected” – The tool scans all .exe files inside the selected folders (and their subfolders) and creates outbound firewall rules for each protocol you chose.

Click “Restore All” – Removes every rule that was created by this tool, instantly restoring internet access.

📦 Installation & Usage
System Requirements
Windows 7 / 8 / 10 / 11 (32‑bit or 64‑bit)

Administrator privileges (required to modify firewall rules)

Steps
Download the latest FirewallBlocker.exe from the Releases page.

Place the .exe anywhere you like (Desktop, Documents, etc.).

Right‑click the file and select “Run as administrator” – this is mandatory.

Use the interface:

Enter a folder path or click Browse…

Select a protocol from the dropdown

Click Add Path

Check the boxes for folders you want to block

Click 🚫 Block Selected

To undo everything, click ✅ Restore All.

💡 Optional: Create a protocols.txt file in the same folder as the .exe. List one protocol per line (e.g., TCP, UDP, ICMPv4). If this file exists, the tool will use those protocols instead of the dropdown selection.

🎯 Why I Built This
As a user of SOLIDWORKS and CATIA, I was frustrated by:

Frequent license validation attempts that required an active internet connection.

Automatic updates that sometimes broke custom configurations.

Background telemetry services that consumed bandwidth.

Instead of editing the hosts file or disabling network adapters manually, I wanted a simple, visual tool that could:

Block all .exe files inside a folder (and subfolders) with one action.

Allow me to selectively enable/disable blocking per folder.

Be fully reversible with a single click.

This tool solved all those problems – and now it’s available for anyone who needs similar control.

✅ Advantages
Advantage	Details
No installation	Runs directly from .exe – perfect for portable drives or temporary use.
Deep scanning	Recursively finds every .exe inside the chosen folders.
Protocol flexibility	You can block TCP, UDP, ICMP, or any custom protocol.
Bulk operations	Select/deselect all folders, remove multiple at once.
Safe & reversible	All changes are made to Windows Firewall; nothing is deleted or modified on disk.
Lightweight	~300 KB executable, uses minimal system resources.
No dependencies	Uses only the Windows API – no .NET, no runtime libraries.
⚠️ Disadvantages / Limitations
Limitation	Explanation
Administrator rights required	You must run the tool as admin to modify firewall rules.
Local network licenses	If your application uses a network license server (on the same LAN), blocking its internet access will also block local license validation.
Hidden services	Some applications have background services installed outside the main folder (e.g., in System32). These may not be blocked unless you explicitly add their paths.
Firewall rules only	This tool does not modify hosts files, proxy settings, or DNS – it only uses Windows Firewall outbound rules.
Manual updates	If the application is updated or reinstalled, you may need to re‑add its new folder path.
🔧 Building from Source
If you want to compile the project yourself:

Prerequisites
MinGW-w64 (GCC) – download from winlibs.com

Windows SDK headers (included with MinGW)

Steps
Clone the repository:

bash
git clone https://github.com/mahanneman/FirewallBlocker.git
cd FirewallBlocker
Place the mingw32 or mingw64 folder inside the project directory.

Run the compile script:

bash
compile.bat
Or manually:

bash
g++ -static -mwindows -o FirewallBlocker.exe FirewallBlocker.cpp -lcomctl32 -lshell32 -lshlwapi -lgdi32 -luser32 -lole32
📂 Folder Structure (for developers)
text
FirewallBlocker/
├── FirewallBlocker.cpp      # Main source code
├── compile.bat              # Build script (optional)
├── protocols.txt            # (Optional) Custom protocol list
└── README.md                # This file
🧪 How to Test
Add a test folder (e.g., C:\Windows\System32\drivers\etc) – it contains no .exe files, so it’s safe.

Add a real application folder (e.g., D:\Program Files\SOLIDWORKS Corp).

Click Block Selected.

Open Windows Firewall with Advanced Security (wf.msc) and look for rules named Block_App_* under Outbound Rules.

Launch the application and verify it cannot access the internet.

🛡️ Security & Privacy
This tool does not collect, send, or store any data.

All firewall changes are made locally using netsh advfirewall.

The source code is fully open for inspection – no hidden payloads.
