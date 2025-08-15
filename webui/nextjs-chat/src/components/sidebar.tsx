import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Plus, MessageSquare, Trash2, Settings, User, Pencil, Menu, Flashlight, PanelLeftClose, PanelLeftOpen, MoreHorizontal, Sparkles } from "lucide-react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { ChatSession } from "@/types/chat";
import { useTheme } from "next-themes";
import { useEffect, useState, useRef } from "react";

interface SidebarProps {
  sessions: ChatSession[];
  currentSessionId?: string;
  onNewChat: () => void;
  onSelectSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
  onRenameSession?: (sessionId: string, newTitle: string) => void;
  onToggleFavoriteSession: (sessionId: string) => void;
}

export function Sidebar({
  sessions,
  currentSessionId,
  onNewChat,
  onSelectSession,
  onDeleteSession,
  onRenameSession,
  onToggleFavoriteSession,
}: SidebarProps) {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [search, setSearch] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const [open, setOpen] = useState(true);
  const [showTooltip, setShowTooltip] = useState(false);
  const tooltipTimeout = useRef<NodeJS.Timeout | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  // 懐中電灯アイコンのツールチップ用
  const [showThemeTooltip, setShowThemeTooltip] = useState(false);
  const themeTooltipTimeout = useRef<NodeJS.Timeout | null>(null);
  // 設定アイコンのツールチップ用
  const [showSettingsTooltip, setShowSettingsTooltip] = useState(false);
  const settingsTooltipTimeout = useRef<NodeJS.Timeout | null>(null);
  // 懐中電灯アイコンのフェード用
  const [fade, setFade] = useState(false);
  const prevTheme = useRef<string | undefined>(theme);
  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (editingId && inputRef.current) {
      inputRef.current.focus();
    }
  }, [editingId]);

  // サイドバー開閉時にツールチップを必ず非表示にする
  useEffect(() => {
    setShowTooltip(false);
  }, [open]);

  useEffect(() => {
    if (prevTheme.current !== undefined && prevTheme.current !== theme) {
      setFade(true);
      const t = setTimeout(() => setFade(false), 350); // 350msでフェード
      prevTheme.current = theme;
      return () => clearTimeout(t);
    }
    prevTheme.current = theme;
  }, [theme]);

  const filteredSessions = sessions.filter((session) =>
    session.title.toLowerCase().includes(search.toLowerCase())
  );

  const handleEdit = (session: ChatSession) => {
    setEditingId(session.id);
    setEditValue(session.title);
  };

  const handleEditSubmit = (session: ChatSession) => {
    if (onRenameSession && editValue.trim() && editValue !== session.title) {
      onRenameSession(session.id, editValue.trim());
    }
    setEditingId(null);
  };

  // お気に入り・通常履歴分割
  const favoriteSessions = sessions.filter(s => s.isFavorite);
  const normalSessions = sessions; // すべてのチャットを通常履歴に表示
  // お気に入り「もっと見る」ロジック
  const [showAllFavorites, setShowAllFavorites] = useState(false);
  const FAVORITE_LIMIT = 3;
  const visibleFavorites = showAllFavorites ? favoriteSessions : favoriteSessions.slice(0, FAVORITE_LIMIT);

  // サイドバーの色切り替え（mounted前は空文字でSSR/CSR不一致を防ぐ）
  const sidebarBg = !mounted
    ? ""
    : theme === "dark"
      ? "bg-[#202123] text-white border-black/10"
      : "bg-[#f5f5f7] text-gray-900 border-gray-200";
  const borderColor = !mounted
    ? ""
    : theme === "dark"
      ? "border-black/10"
      : "border-gray-200";
  const inputBg = !mounted
    ? ""
    : theme === "dark"
      ? "bg-[#343541] text-white border-[#444654]"
      : "bg-white text-gray-900 border-gray-300";
  const inputPlaceholder = !mounted
    ? ""
    : "placeholder:text-gray-400";
  const buttonBg = !mounted
    ? ""
    : theme === "dark"
      ? "bg-[#343541] hover:bg-[#444654] text-white"
      : "bg-[#e5e7eb] hover:bg-[#d1d5db] text-gray-900";
  const menuText = !mounted
    ? ""
    : theme === "dark"
      ? "text-gray-300 hover:bg-[#343541]"
      : "text-gray-700 hover:bg-gray-200";

  if (!open) {
    return (
      <>
        <div className="fixed left-2 top-2 z-30">
          <button
            className="p-2 rounded-md bg-transparent hover:bg-gray-300 dark:hover:bg-[#23232b] relative"
            onClick={() => setOpen(true)}
            aria-label="サイドバーを開く"
            onMouseEnter={() => {
              if (tooltipTimeout.current) clearTimeout(tooltipTimeout.current);
              tooltipTimeout.current = setTimeout(() => setShowTooltip(true), 200);
            }}
            onMouseLeave={() => {
              if (tooltipTimeout.current) clearTimeout(tooltipTimeout.current);
              setShowTooltip(false);
            }}
          >
            <PanelLeftOpen className="h-5 w-5" />
            {showTooltip && (
              <span className={`absolute left-12 top-1/2 -translate-y-1/2 px-2 py-1 rounded text-xs shadow transition-opacity duration-100 whitespace-nowrap pointer-events-none select-none ${theme === "dark" ? "bg-white text-black" : "bg-black text-white"}`}>
                サイドバーを開く
              </span>
            )}
          </button>
        </div>
        {/* 懐中電灯アイコンはサイドバーを閉じているときは非表示にする（削除） */}
      </>
    );
  }

  return (
    <aside className={`fixed left-0 top-0 h-full w-64 ${sidebarBg} border-r flex flex-col z-20 transition-all duration-200`}>
      {/* 開閉ボタン＋カスタムツールチップ */}
      <div className="absolute right-2 top-2 z-30">
        <button
          className="p-2 rounded-md bg-transparent hover:bg-gray-300 dark:hover:bg-[#23232b] relative"
          onClick={() => setOpen(false)}
          aria-label="サイドバーを閉じる"
          onMouseEnter={() => {
            if (tooltipTimeout.current) clearTimeout(tooltipTimeout.current);
            tooltipTimeout.current = setTimeout(() => setShowTooltip(true), 200);
          }}
          onMouseLeave={() => {
            if (tooltipTimeout.current) clearTimeout(tooltipTimeout.current);
            setShowTooltip(false);
          }}
        >
          <PanelLeftClose className="h-5 w-5" />
          {showTooltip && (
            <span className={`absolute right-12 top-1/2 -translate-y-1/2 px-2 py-1 rounded text-xs shadow transition-opacity duration-100 whitespace-nowrap pointer-events-none select-none ${theme === "dark" ? "bg-white text-black" : "bg-black text-white"}`}>
              サイドバーを閉じる
            </span>
          )}
        </button>
      </div>
      {/* ヘッダー */}
      <div className={`flex items-center h-16 px-6 border-b font-bold text-lg tracking-wide select-none ${borderColor}`}>
        Okamichan
      </div>
      {/* チャット検索 */}
      <div className={`p-4 border-b ${borderColor}`}>
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="チャットを検索"
          className={`w-full rounded-md px-3 py-2 text-sm ${inputBg} ${inputPlaceholder} border focus:outline-none focus:ring-2 focus:ring-primary`}
        />
        <Button onClick={onNewChat} className={`w-full mt-3 ${buttonBg}`} size="sm">
          <Plus className="h-4 w-4 mr-2" />
          新しいチャット
        </Button>
      </div>
      {/* お気に入り＋最近エリア全体を1つのScrollAreaでラップ */}
      <ScrollArea className="flex-1 max-h-[calc(100vh-220px)]">
        <div className="pb-20">
          {/* お気に入りエリア */}
          <div className="px-4 pt-4 pb-2">
            <div className="font-bold text-sm mb-2">お気に入り</div>
            <div className="flex flex-col gap-1">
              {favoriteSessions.length > 0 && visibleFavorites.map(session => (
                <div
                  key={session.id}
                  className={`group relative flex items-center gap-3 rounded-lg p-2 text-sm cursor-pointer transition-colors ${currentSessionId === session.id ? (theme === "dark" ? "bg-[#343541] text-white" : "bg-gray-200 text-gray-900") : (theme === "dark" ? "hover:bg-[#2a2b32] text-gray-200" : "hover:bg-gray-100 text-gray-900")}`}
                  onClick={() => onSelectSession(session.id)}
                >
                  <MessageSquare className="h-4 w-4 shrink-0" />
                  <span className="truncate font-medium flex-1">{session.title}</span>
                  {/* 三点メニュー */}
                  <DropdownMenu.Root>
                    <DropdownMenu.Trigger asChild>
                      <Button variant="ghost" size="icon" className="h-6 w-6 p-0 text-gray-400 hover:text-primary">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenu.Trigger>
                    <DropdownMenu.Content sideOffset={4} className="z-50 min-w-[160px] rounded-md bg-white dark:bg-[#23232b] p-2 shadow-lg border border-gray-200 dark:border-[#444654]">
                      <DropdownMenu.Item className="flex items-center gap-2 px-3 py-2 rounded-md text-sm cursor-pointer hover:bg-gray-100 dark:hover:bg-[#343541] dark:text-black !dark:text-black"
                        onClick={e => { e.stopPropagation(); onToggleFavoriteSession(session.id); }}
                        style={{ color: theme === 'dark' ? 'black' : 'inherit' }}>
                        <span className="dark:text-black !dark:text-black" style={{ color: theme === 'dark' ? 'black' : 'inherit' }}>お気に入りから削除</span>
                      </DropdownMenu.Item>
                      <DropdownMenu.Item className="flex items-center gap-2 px-3 py-2 rounded-md text-sm cursor-pointer hover:bg-red-100 dark:hover:bg-red-900 text-red-600 dark:text-red-400"
                        onClick={e => { e.stopPropagation(); onDeleteSession(session.id); }}>
                        <span>削除する</span>
                      </DropdownMenu.Item>
                    </DropdownMenu.Content>
                  </DropdownMenu.Root>
                </div>
              ))}
              {favoriteSessions.length > FAVORITE_LIMIT && !showAllFavorites && (
                <button className="text-xs text-gray-500 hover:underline mt-1" onClick={() => setShowAllFavorites(true)}>
                  もっと見る
                </button>
              )}
              {favoriteSessions.length > FAVORITE_LIMIT && showAllFavorites && (
                <button className="text-xs text-gray-500 hover:underline mt-1" onClick={() => setShowAllFavorites(false)}>
                  折りたたむ
                </button>
              )}
            </div>
          </div>
          {/* 最近エリア */}
          <div className="px-4 pt-4 pb-2">
            <div className="font-bold text-sm mb-2">最近</div>
          </div>
          {normalSessions.length === 0 ? (
            <div className="text-center text-gray-400 py-8">
              <MessageSquare className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p className="text-sm">チャット履歴がありません</p>
              <p className="text-xs">新しいチャットを開始してください</p>
            </div>
          ) : (
            normalSessions.map((session) => (
              <div
                key={session.id}
                className={`group relative flex items-center gap-3 rounded-lg p-3 text-sm cursor-pointer transition-colors ${currentSessionId === session.id ? (theme === "dark" ? "bg-[#343541] text-white" : "bg-gray-200 text-gray-900") : (theme === "dark" ? "hover:bg-[#2a2b32] text-gray-200" : "hover:bg-gray-100 text-gray-900")}`}
                onClick={() => onSelectSession(session.id)}
              >
                <MessageSquare className="h-4 w-4 shrink-0" />
                <div className="flex-1 min-w-0">
                  {editingId === session.id ? (
                    <input
                      ref={inputRef}
                      type="text"
                      value={editValue}
                      onChange={e => setEditValue(e.target.value)}
                      onBlur={() => handleEditSubmit(session)}
                      onKeyDown={e => {
                        if (e.key === "Enter") handleEditSubmit(session);
                        if (e.key === "Escape") setEditingId(null);
                      }}
                      className={`w-full rounded-md px-2 py-1 text-sm ${inputBg} border focus:outline-none`}
                    />
                  ) : (
                    <div className="flex items-center gap-1">
                      <span className="truncate font-medium" onDoubleClick={() => handleEdit(session)}>{session.title}</span>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-5 w-5 p-0 text-gray-400 hover:text-primary"
                        onClick={e => {
                          e.stopPropagation();
                          handleEdit(session);
                        }}
                        tabIndex={-1}
                      >
                        <Pencil className="h-3 w-3" />
                      </Button>
                    </div>
                  )}
                </div>
                {/* 三点メニュー */}
                <DropdownMenu.Root>
                  <DropdownMenu.Trigger asChild>
                    <Button variant="ghost" size="icon" className="h-6 w-6 p-0 text-gray-400 hover:text-primary">
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenu.Trigger>
                  <DropdownMenu.Content sideOffset={4} className="z-50 min-w-[160px] rounded-md bg-white dark:bg-[#23232b] p-2 shadow-lg border border-gray-200 dark:border-[#444654]">
                    <DropdownMenu.Item className="flex items-center gap-2 px-3 py-2 rounded-md text-sm cursor-pointer hover:bg-gray-100 dark:hover:bg-[#e5e7eb] dark:text-black !dark:text-black"
                      onClick={e => { e.stopPropagation(); onToggleFavoriteSession(session.id); }}
                      style={{ color: theme === 'dark' ? 'black' : 'inherit' }}>
                      <span className="dark:text-black !dark:text-black" style={{ color: theme === 'dark' ? 'black' : 'inherit' }}>{session.isFavorite ? 'お気に入りから削除' : 'お気に入りに追加'}</span>
                    </DropdownMenu.Item>
                    <DropdownMenu.Item className="flex items-center gap-2 px-3 py-2 rounded-md text-sm cursor-pointer hover:bg-red-100 dark:hover:bg-red-900 text-red-600 dark:text-red-400"
                      onClick={e => { e.stopPropagation(); onDeleteSession(session.id); }}>
                      <span>削除する</span>
                    </DropdownMenu.Item>
                  </DropdownMenu.Content>
                </DropdownMenu.Root>
              </div>
            ))
          )}
        </div>
      </ScrollArea>
      {/* 下部メニュー */}
      <div className={`absolute left-0 bottom-0 w-full border-t ${borderColor} p-4 flex flex-row items-center justify-center gap-4 bg-inherit`}>
        {/* 設定アイコン＋カスタムツールチップ */}
        <div className="relative">
          <Button variant="ghost" size="icon" className={'p-1 h-7 w-7 flex items-center justify-center rounded-full bg-gray-200 dark:bg-[#23232b] border border-gray-300 dark:border-white'} aria-label="設定"
            onMouseEnter={() => {
              settingsTooltipTimeout.current && clearTimeout(settingsTooltipTimeout.current);
              settingsTooltipTimeout.current = setTimeout(() => setShowSettingsTooltip(true), 200);
            }}
            onMouseLeave={() => {
              settingsTooltipTimeout.current && clearTimeout(settingsTooltipTimeout.current);
              setShowSettingsTooltip(false);
            }}
          >
            <Settings className="h-3.5 w-3.5 text-black" />
          </Button>
          {showSettingsTooltip && (
            <span className={`absolute left-1/2 -translate-x-1/2 bottom-12 px-2 py-1 rounded text-xs shadow transition-opacity duration-100 whitespace-nowrap pointer-events-none select-none ${theme === "dark" ? "bg-white text-black" : "bg-black text-white"}`}>
              設定
            </span>
          )}
        </div>
        {/* 懐中電灯アイコン＋カスタムツールチップ */}
        {mounted && (
          <div className="relative">
            <button
              className="p-1 h-7 w-7 flex items-center justify-center rounded-full bg-gray-200 dark:bg-[#23232b] shadow border border-gray-300 dark:border-white"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              aria-label="テーマ切り替え"
              onMouseEnter={() => {
                themeTooltipTimeout.current && clearTimeout(themeTooltipTimeout.current);
                themeTooltipTimeout.current = setTimeout(() => setShowThemeTooltip(true), 200);
              }}
              onMouseLeave={() => {
                themeTooltipTimeout.current && clearTimeout(themeTooltipTimeout.current);
                setShowThemeTooltip(false);
              }}
            >
              <span className="relative flex items-center">
                <Flashlight className={`h-4 w-4 transition-opacity duration-300 ${fade ? 'opacity-0' : 'opacity-100'} ${theme === 'dark' ? 'text-black' : ''}`} />
              </span>
            </button>
            {showThemeTooltip && (
              <span className={`absolute left-1/2 -translate-x-1/2 bottom-12 px-2 py-1 rounded text-xs shadow transition-opacity duration-100 whitespace-nowrap pointer-events-none select-none ${theme === "dark" ? "bg-white text-black" : "bg-black text-white"}`}>
                {theme === "light" ? "ライトテーマ" : "ダークテーマ"}
              </span>
            )}
          </div>
        )}
      </div>
    </aside>
  );
} 