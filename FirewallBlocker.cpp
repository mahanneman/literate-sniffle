#define WINVER 0x0600
#define _WIN32_WINNT 0x0600
#define _WIN32_IE 0x0600

#include <windows.h>
#include <commctrl.h>
#include <shlobj.h>
#include <shlwapi.h>
#include <string>
#include <vector>
#include <fstream>
#include <algorithm>
#include "resource.h"


#define IDC_LIST_PATHS        1001
#define IDC_EDIT_PATH         1002
#define IDC_BTN_BROWSE        1003
#define IDC_BTN_ADD           1004
#define IDC_BTN_REMOVE        1005
#define IDC_BTN_BLOCK         1006
#define IDC_BTN_UNBLOCK       1007
#define IDC_BTN_SELECT_ALL    1008
#define IDC_BTN_DESELECT_ALL  1009
#define IDC_HEADER            1010
#define IDC_FOOTER            1011
#define IDC_COMBO_PROTOCOL    1012
#define IDC_GITHUB            1013

HWND g_hList;
HWND g_hEdit;
HWND g_hCombo;
HINSTANCE g_hInst;

HFONT g_hFont;
HFONT g_hFontHeader;
HFONT g_hFontSmall;
HBRUSH g_hBrushBlack;
HBRUSH g_hBrushCyan;

// رنگ‌های جدید (نارنجی روشن به جای سفید)
COLORREF g_crCyan = RGB(0, 200, 200);          // فیروزه‌ای
COLORREF g_crGold = RGB(255, 215, 0);          // طلایی
COLORREF g_crOrange = RGB(255, 180, 50);       // نارنجی روشن (جایگزین سفید)
COLORREF g_crWhite = RGB(255, 255, 255);       // سفید (برای برخی موارد)

// ساختار برای ذخیره مسیر و پروتکل
struct PathItem {
    std::string path;
    std::string protocol;
};

std::vector<PathItem> g_pathItems;

// ================== توابع کمکی ==================

std::string BrowseForFolder(HWND hWnd) {
    BROWSEINFOA bi = { 0 };
    bi.hwndOwner = hWnd;
    bi.lpszTitle = "Select the installation folder";
    bi.ulFlags = BIF_RETURNONLYFSDIRS | BIF_NEWDIALOGSTYLE;

    LPITEMIDLIST pidl = SHBrowseForFolderA(&bi);
    if (pidl != 0) {
        char path[MAX_PATH];
        if (SHGetPathFromIDListA(pidl, path)) {
            IMalloc* imalloc = 0;
            if (SUCCEEDED(SHGetMalloc(&imalloc))) {
                imalloc->Free(pidl);
                imalloc->Release();
            }
            return std::string(path);
        }
    }
    return "";
}

void FindExeFiles(const std::string& folder, std::vector<std::string>& exeList) {
    std::string searchPath = folder + "\\*.exe";
    WIN32_FIND_DATAA fd;
    HANDLE hFind = FindFirstFileA(searchPath.c_str(), &fd);
    if (hFind != INVALID_HANDLE_VALUE) {
        do {
            if (!(fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) {
                exeList.push_back(folder + "\\" + fd.cFileName);
            }
        } while (FindNextFileA(hFind, &fd));
        FindClose(hFind);
    }

    searchPath = folder + "\\*";
    hFind = FindFirstFileA(searchPath.c_str(), &fd);
    if (hFind != INVALID_HANDLE_VALUE) {
        do {
            if (fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
                if (strcmp(fd.cFileName, ".") != 0 && strcmp(fd.cFileName, "..") != 0) {
                    FindExeFiles(folder + "\\" + fd.cFileName, exeList);
                }
            }
        } while (FindNextFileA(hFind, &fd));
        FindClose(hFind);
    }
}

void ExecuteBlock(const std::vector<std::string>& paths) {
    if (paths.empty()) {
        MessageBoxA(NULL, "No paths selected!", "Error", MB_OK | MB_ICONERROR);
        return;
    }

    std::vector<std::string> protocols;
    std::ifstream configFile("protocols.txt");
    if (configFile.is_open()) {
        std::string line;
        while (std::getline(configFile, line)) {
            line.erase(0, line.find_first_not_of(" \t\r\n"));
            line.erase(line.find_last_not_of(" \t\r\n") + 1);
            if (!line.empty() && line[0] != '#') {
                protocols.push_back(line);
            }
        }
        configFile.close();
    }

    if (protocols.empty()) {
        protocols.push_back("TCP");
        protocols.push_back("UDP");
    }

    std::vector<std::string> allExes;
    for (const auto& p : paths) {
        FindExeFiles(p, allExes);
    }

    if (allExes.empty()) {
        MessageBoxA(NULL, "No .exe files found!", "Info", MB_OK | MB_ICONINFORMATION);
        return;
    }

    std::string tempPath = std::string(getenv("TEMP")) + "\\block_firewall.bat";
    std::ofstream batFile(tempPath);
    if (!batFile.is_open()) {
        MessageBoxA(NULL, "Failed to create script!", "Error", MB_OK | MB_ICONERROR);
        return;
    }

    batFile << "@echo off\n";
    batFile << "echo Blocking " << allExes.size() << " applications for protocols: ";
    for (const auto& p : protocols) batFile << p << " ";
    batFile << "\n\n";

    int count = 0;
    for (const auto& exe : allExes) {
        for (const auto& proto : protocols) {
            std::string ruleName = "Block_App_" + std::to_string(count) + "_" + proto;
            batFile << "netsh advfirewall firewall add rule name=\"" << ruleName 
                    << "\" dir=out program=\"" << exe 
                    << "\" protocol=" << proto 
                    << " action=block >nul 2>&1\n";
        }
        count++;
    }

    batFile << "\necho DONE! " << count << " applications blocked.\n";
    batFile << "timeout /t 3 >nul\n";
    batFile << "exit\n";
    batFile.close();

    STARTUPINFOA si = { sizeof(si) };
    PROCESS_INFORMATION pi;
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;

    std::string cmd = "cmd.exe /c \"" + tempPath + "\"";
    if (CreateProcessA(NULL, (LPSTR)cmd.c_str(), NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi)) {
        WaitForSingleObject(pi.hProcess, INFINITE);
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
        MessageBoxA(NULL, "Applications blocked successfully!", "Success", MB_OK | MB_ICONINFORMATION);
    } else {
        MessageBoxA(NULL, "Failed to execute firewall commands!", "Error", MB_OK | MB_ICONERROR);
    }
    DeleteFileA(tempPath.c_str());
}

void ExecuteUnblock() {
    std::string tempPath = std::string(getenv("TEMP")) + "\\unblock_firewall.bat";
    std::ofstream batFile(tempPath);
    if (!batFile.is_open()) {
        MessageBoxA(NULL, "Failed to create script!", "Error", MB_OK | MB_ICONERROR);
        return;
    }

    batFile << "@echo off\n";
    batFile << "echo Removing all Block_App_* rules...\n";
    batFile << "for /f \"tokens=*\" %%a in ('netsh advfirewall firewall show rule name=all ^| find \"Block_App_\"') do (\n";
    batFile << "    netsh advfirewall firewall delete rule name=\"%%a\" >nul 2>&1\n";
    batFile << ")\n";
    batFile << "echo DONE! All rules removed.\n";
    batFile << "timeout /t 3 >nul\n";
    batFile << "exit\n";
    batFile.close();

    STARTUPINFOA si = { sizeof(si) };
    PROCESS_INFORMATION pi;
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;

    std::string cmd = "cmd.exe /c \"" + tempPath + "\"";
    if (CreateProcessA(NULL, (LPSTR)cmd.c_str(), NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi)) {
        WaitForSingleObject(pi.hProcess, INFINITE);
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
        MessageBoxA(NULL, "All firewall rules removed!", "Success", MB_OK | MB_ICONINFORMATION);
    } else {
        MessageBoxA(NULL, "Failed to execute unblock command!", "Error", MB_OK | MB_ICONERROR);
    }
    DeleteFileA(tempPath.c_str());
}

void RefreshListView() {
    ListView_DeleteAllItems(g_hList);
    for (const auto& item : g_pathItems) {
        LVITEMA lvi = {0};
        lvi.mask = LVIF_TEXT;
        
        // ستون اول: مسیر
        lvi.pszText = (LPSTR)item.path.c_str();
        int index = ListView_InsertItem(g_hList, &lvi);
        
        // ستون دوم: پروتکل
        ListView_SetItemText(g_hList, index, 1, (LPSTR)item.protocol.c_str());
        
        // تیک پیش‌فرض فعال
        ListView_SetCheckState(g_hList, index, TRUE);
    }
}

void AddPathToList(const std::string& path, const std::string& protocol) {
    PathItem newItem;
    newItem.path = path;
    newItem.protocol = protocol;
    g_pathItems.push_back(newItem);
    RefreshListView();
}

// ================== Window Procedure ==================

LRESULT CALLBACK WndProc(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    switch (msg) {
    case WM_CREATE: {
        g_hBrushBlack = CreateSolidBrush(RGB(0, 0, 0));
        g_hBrushCyan = CreateSolidBrush(g_crCyan);

        g_hFont = CreateFont(14, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE,
                             DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
                             DEFAULT_QUALITY, DEFAULT_PITCH | FF_DONTCARE, "Segoe UI");
        g_hFontHeader = CreateFont(18, 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE,
                                   DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
                                   DEFAULT_QUALITY, DEFAULT_PITCH | FF_DONTCARE, "Segoe UI");
        g_hFontSmall = CreateFont(12, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE,
                                  DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
                                  DEFAULT_QUALITY, DEFAULT_PITCH | FF_DONTCARE, "Segoe UI");

        // ========== هدر ==========
        HWND hHeader = CreateWindowA("STATIC", "Developed by Mahan Neman MA.AD.GH",
                                     WS_CHILD | WS_VISIBLE | SS_CENTER,
                                     20, 10, 580, 30, hWnd, (HMENU)IDC_HEADER, g_hInst, NULL);
        SendMessage(hHeader, WM_SETFONT, (WPARAM)g_hFontHeader, TRUE);

        // GitHub
        HWND hGitHub = CreateWindowA("STATIC", "GitHub: github.com/mahanneman",
                                     WS_CHILD | WS_VISIBLE | SS_CENTER,
                                     20, 40, 580, 20, hWnd, (HMENU)IDC_GITHUB, g_hInst, NULL);
        SendMessage(hGitHub, WM_SETFONT, (WPARAM)g_hFontSmall, TRUE);

        // ========== بخش مسیر ==========
        CreateWindowA("STATIC", "Enter Application Path:", WS_CHILD | WS_VISIBLE,
                      20, 75, 150, 20, hWnd, NULL, g_hInst, NULL);

        g_hEdit = CreateWindowA("EDIT", "", WS_CHILD | WS_VISIBLE | WS_BORDER,
                                20, 100, 400, 25, hWnd, (HMENU)IDC_EDIT_PATH, g_hInst, NULL);
        SendMessage(g_hEdit, WM_SETFONT, (WPARAM)g_hFont, TRUE);

        HWND hBtnBrowse = CreateWindowA("BUTTON", "Browse...", WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON,
                                        430, 100, 80, 25, hWnd, (HMENU)IDC_BTN_BROWSE, g_hInst, NULL);
        SendMessage(hBtnBrowse, WM_SETFONT, (WPARAM)g_hFont, TRUE);

        // ========== کادر انتخاب پروتکل ==========
        CreateWindowA("STATIC", "Protocol:", WS_CHILD | WS_VISIBLE,
                      520, 75, 80, 20, hWnd, NULL, g_hInst, NULL);

        g_hCombo = CreateWindowA("COMBOBOX", "", WS_CHILD | WS_VISIBLE | CBS_DROPDOWNLIST | WS_VSCROLL,
                                 520, 100, 100, 100, hWnd, (HMENU)IDC_COMBO_PROTOCOL, g_hInst, NULL);
        SendMessage(g_hCombo, WM_SETFONT, (WPARAM)g_hFont, TRUE);

        // اضافه کردن آیتم‌ها به ComboBox
        SendMessageA(g_hCombo, CB_ADDSTRING, 0, (LPARAM)"TCP");
        SendMessageA(g_hCombo, CB_ADDSTRING, 0, (LPARAM)"UDP");
        SendMessageA(g_hCombo, CB_ADDSTRING, 0, (LPARAM)"ICMPv4");
        SendMessageA(g_hCombo, CB_ADDSTRING, 0, (LPARAM)"ICMPv6");
        SendMessageA(g_hCombo, CB_ADDSTRING, 0, (LPARAM)"GRE");
        SendMessageA(g_hCombo, CB_ADDSTRING, 0, (LPARAM)"IGMP");
        SendMessageA(g_hCombo, CB_ADDSTRING, 0, (LPARAM)"ESP");
        SendMessageA(g_hCombo, CB_ADDSTRING, 0, (LPARAM)"AH");
        SendMessage(g_hCombo, CB_SETCURSEL, 0, 0); // انتخاب پیش‌فرض TCP

        // ========== دکمه Add Path ==========
        HWND hBtnAdd = CreateWindowA("BUTTON", "Add Path", WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON,
                                     520, 135, 100, 25, hWnd, (HMENU)IDC_BTN_ADD, g_hInst, NULL);
        SendMessage(hBtnAdd, WM_SETFONT, (WPARAM)g_hFont, TRUE);

        // ========== لیست‌ویو ==========
        CreateWindowA("STATIC", "Selected Paths (Check to block):", WS_CHILD | WS_VISIBLE,
                      20, 140, 250, 20, hWnd, NULL, g_hInst, NULL);

        g_hList = CreateWindowA("SysListView32", NULL,
                                WS_CHILD | WS_VISIBLE | WS_BORDER | WS_VSCROLL | WS_HSCROLL | LVS_REPORT | LVS_SINGLESEL,
                                20, 165, 600, 160, hWnd, (HMENU)IDC_LIST_PATHS, g_hInst, NULL);
        ListView_SetExtendedListViewStyle(g_hList, LVS_EX_CHECKBOXES);

        // ستون اول: مسیر
        LVCOLUMNA col = {0};
        col.mask = LVCF_WIDTH | LVCF_TEXT;
        col.pszText = (LPSTR)"Path";
        col.cx = 450;
        ListView_InsertColumn(g_hList, 0, &col);

        // ستون دوم: پروتکل
        col.pszText = (LPSTR)"Protocol";
        col.cx = 110;
        ListView_InsertColumn(g_hList, 1, &col);

        SendMessage(g_hList, WM_SETFONT, (WPARAM)g_hFont, TRUE);

        // ========== دکمه‌های پایین ==========
        int btnY = 345;
        HWND hBtnSelAll = CreateWindowA("BUTTON", " Select All", WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON,
                                        20, btnY, 100, 30, hWnd, (HMENU)IDC_BTN_SELECT_ALL, g_hInst, NULL);
        SendMessage(hBtnSelAll, WM_SETFONT, (WPARAM)g_hFont, TRUE);

        HWND hBtnDeselAll = CreateWindowA("BUTTON", "Deselect All", WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON,
                                          130, btnY, 100, 30, hWnd, (HMENU)IDC_BTN_DESELECT_ALL, g_hInst, NULL);
        SendMessage(hBtnDeselAll, WM_SETFONT, (WPARAM)g_hFont, TRUE);

        HWND hBtnRemove = CreateWindowA("BUTTON", "Remove Selected", WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON,
                                        240, btnY, 110, 30, hWnd, (HMENU)IDC_BTN_REMOVE, g_hInst, NULL);
        SendMessage(hBtnRemove, WM_SETFONT, (WPARAM)g_hFont, TRUE);

        HWND hBtnBlock = CreateWindowA("BUTTON", "Block Selected", WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON,
                                       360, btnY, 120, 30, hWnd, (HMENU)IDC_BTN_BLOCK, g_hInst, NULL);
        SendMessage(hBtnBlock, WM_SETFONT, (WPARAM)g_hFont, TRUE);

        HWND hBtnUnblock = CreateWindowA("BUTTON", "Restore All", WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON,
                                         490, btnY, 110, 30, hWnd, (HMENU)IDC_BTN_UNBLOCK, g_hInst, NULL);
        SendMessage(hBtnUnblock, WM_SETFONT, (WPARAM)g_hFont, TRUE);

        // ========== فوتر (ضرب‌المثل ایرانی) ==========
        HWND hFooter = CreateWindowA("STATIC", "A thousand-mile journey begins with a single step",
                                     WS_CHILD | WS_VISIBLE | SS_CENTER,
                                     20, 400, 600, 25, hWnd, (HMENU)IDC_FOOTER, g_hInst, NULL);
        SendMessage(hFooter, WM_SETFONT, (WPARAM)g_hFontHeader, TRUE);

        break;
    }

    // ========== رنگ‌آمیزی ==========
    case WM_CTLCOLORSTATIC: {
        HDC hdcStatic = (HDC)wParam;
        HWND hCtl = (HWND)lParam;
        int ctrlId = GetDlgCtrlID(hCtl);

        SetBkMode(hdcStatic, TRANSPARENT);

        if (ctrlId == IDC_HEADER) {
            SetTextColor(hdcStatic, g_crGold);
            return (LRESULT)g_hBrushBlack;
        } else if (ctrlId == IDC_GITHUB) {
            SetTextColor(hdcStatic, RGB(100, 200, 255)); // آبی روشن برای GitHub
            return (LRESULT)g_hBrushBlack;
        } else if (ctrlId == IDC_FOOTER) {
            SetTextColor(hdcStatic, g_crCyan);
            return (LRESULT)g_hBrushBlack;
        } else {
            // رنگ نارنجی روشن به جای سفید برای بقیه استاتیک‌ها
            SetTextColor(hdcStatic, g_crOrange);
            return (LRESULT)g_hBrushBlack;
        }
    }

    case WM_CTLCOLORBTN: {
        HDC hdcBtn = (HDC)wParam;
        SetBkMode(hdcBtn, TRANSPARENT);
        SetTextColor(hdcBtn, g_crWhite);
        SetBkColor(hdcBtn, g_crCyan);
        return (LRESULT)g_hBrushCyan;
    }

    case WM_CTLCOLOREDIT: {
        HDC hdcEdit = (HDC)wParam;
        SetTextColor(hdcEdit, g_crOrange);
        SetBkColor(hdcEdit, RGB(50, 50, 50));
        HBRUSH hBrush = CreateSolidBrush(RGB(50, 50, 50));
        return (LRESULT)hBrush;
    }

    case WM_CTLCOLORLISTBOX: {
        HDC hdcLV = (HDC)wParam;
        SetTextColor(hdcLV, g_crOrange);
        SetBkColor(hdcLV, RGB(40, 40, 40));
        HBRUSH hBrush = CreateSolidBrush(RGB(40, 40, 40));
        return (LRESULT)hBrush;
    }

    case WM_ERASEBKGND: {
        HDC hdc = (HDC)wParam;
        RECT rc;
        GetClientRect(hWnd, &rc);
        FillRect(hdc, &rc, g_hBrushBlack);
        return TRUE;
    }

    case WM_COMMAND: {
        int id = LOWORD(wParam);
        switch (id) {
        case IDC_BTN_BROWSE: {
            std::string folder = BrowseForFolder(hWnd);
            if (!folder.empty()) SetWindowTextA(g_hEdit, folder.c_str());
            break;
        }
        case IDC_BTN_ADD: {
            char buffer[MAX_PATH];
            GetWindowTextA(g_hEdit, buffer, MAX_PATH);
            if (strlen(buffer) > 0) {
                // دریافت پروتکل انتخاب شده از ComboBox
                int selIndex = SendMessage(g_hCombo, CB_GETCURSEL, 0, 0);
                char protocol[50] = "TCP";
                if (selIndex != CB_ERR) {
                    SendMessageA(g_hCombo, CB_GETLBTEXT, selIndex, (LPARAM)protocol);
                }

                // بررسی تکراری نبودن
                bool exists = false;
                for (const auto& item : g_pathItems) {
                    if (item.path == buffer) {
                        exists = true;
                        break;
                    }
                }
                if (!exists) {
                    AddPathToList(buffer, protocol);
                } else {
                    MessageBoxA(hWnd, "Path already exists!", "Warning", MB_OK);
                }
            }
            break;
        }
        case IDC_BTN_REMOVE: {
            int sel = ListView_GetNextItem(g_hList, -1, LVNI_SELECTED);
            if (sel != -1 && sel < (int)g_pathItems.size()) {
                g_pathItems.erase(g_pathItems.begin() + sel);
                RefreshListView();
            } else {
                MessageBoxA(hWnd, "Select an item to remove.", "Info", MB_OK);
            }
            break;
        }
        case IDC_BTN_SELECT_ALL: {
            int count = ListView_GetItemCount(g_hList);
            for (int i = 0; i < count; i++) {
                ListView_SetCheckState(g_hList, i, TRUE);
            }
            break;
        }
        case IDC_BTN_DESELECT_ALL: {
            int count = ListView_GetItemCount(g_hList);
            for (int i = 0; i < count; i++) {
                ListView_SetCheckState(g_hList, i, FALSE);
            }
            break;
        }
        case IDC_BTN_BLOCK: {
            std::vector<std::string> selectedPaths;
            int count = ListView_GetItemCount(g_hList);
            for (int i = 0; i < count && i < (int)g_pathItems.size(); i++) {
                if (ListView_GetCheckState(g_hList, i)) {
                    selectedPaths.push_back(g_pathItems[i].path);
                }
            }
            ExecuteBlock(selectedPaths);
            break;
        }
        case IDC_BTN_UNBLOCK: {
            ExecuteUnblock();
            break;
        }
        }
        break;
    }

    case WM_DESTROY:
        DeleteObject(g_hBrushBlack);
        DeleteObject(g_hBrushCyan);
        DeleteObject(g_hFont);
        DeleteObject(g_hFontHeader);
        DeleteObject(g_hFontSmall);
        PostQuitMessage(0);
        break;

    default:
        return DefWindowProc(hWnd, msg, wParam, lParam);
    }
    return 0;
}
int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow) {
    g_hInst = hInstance;
    INITCOMMONCONTROLSEX icc = { sizeof(INITCOMMONCONTROLSEX), ICC_STANDARD_CLASSES | ICC_LISTVIEW_CLASSES };
    InitCommonControlsEx(&icc);

    WNDCLASSEXA wc = { 0 };
    wc.cbSize = sizeof(WNDCLASSEXA);
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInstance;
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.hbrBackground = (HBRUSH)GetStockObject(BLACK_BRUSH);
    wc.lpszClassName = "FirewallBlockerClass";
    

    wc.hIcon = LoadIcon(GetModuleHandle(NULL), MAKEINTRESOURCE(IDI_ICON1));
    
    RegisterClassExA(&wc);

    HWND hWnd = CreateWindowExA(0, "FirewallBlockerClass", "Firewall Blocker",
                                WS_OVERLAPPEDWINDOW & ~WS_MAXIMIZEBOX & ~WS_THICKFRAME,
                                CW_USEDEFAULT, CW_USEDEFAULT, 670, 490,
                                NULL, NULL, hInstance, NULL);
    if (!hWnd) return 0;

    ShowWindow(hWnd, nCmdShow);
    UpdateWindow(hWnd);

    MSG msg;
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }
    return msg.wParam;
}