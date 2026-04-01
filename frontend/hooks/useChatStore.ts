import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';

export interface ChatHistoryItem {
    id: string;
    title: string;
    preview: string;
    timestamp: Date;
}

export interface Message {
    id: string;
    content: string;
    role: 'user' | 'assistant' | 'system';
    timestamp: Date;
    response?: any;
    queryMode?: any;
    isThinking?: boolean;
    currentStep?: string;
    attachedFiles?: { name: string; size: number; type: string }[];
    internetEnabled?: boolean;
}

const STORAGE_KEY = 'local-chat-history';

// Load chats from localStorage
const loadChatsFromStorage = (): ChatHistoryItem[] => {
    if (typeof window === 'undefined') return [];
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (!stored) return [];
        const parsed = JSON.parse(stored);
        return parsed.map((item: any) => ({
            ...item,
            timestamp: new Date(item.timestamp),
        }));
    } catch (error) {
        console.error('Error loading chats from localStorage:', error);
        return [];
    }
};

// Save chats to localStorage
const saveChatsToStorage = (chats: ChatHistoryItem[]): void => {
    if (typeof window === 'undefined') return;
    try {
        const serialized = chats.map(item => ({
            ...item,
            timestamp: item.timestamp.toISOString(),
        }));
        localStorage.setItem(STORAGE_KEY, JSON.stringify(serialized));
    } catch (error) {
        console.error('Error saving chats to localStorage:', error);
    }
};

export function useChatStore() {
    const [chats, setChats] = useState<ChatHistoryItem[]>([]);
    const [loading, setLoading] = useState(true);
    const { user } = useAuth();

    // Load chats from localStorage on mount
    useEffect(() => {
        console.log('useChatStore: Loading chats from localStorage');
        setLoading(true);
        
        const loadedChats = loadChatsFromStorage();
        // Sort by timestamp in descending order (newest first)
        loadedChats.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
        
        console.log('useChatStore: Loaded chats', { count: loadedChats.length });
        setChats(loadedChats);
        setLoading(false);
    }, []);

    // Persist chats to localStorage whenever they change
    useEffect(() => {
        if (!loading) {
            saveChatsToStorage(chats);
        }
    }, [chats, loading]);

    const createChat = async (initialMessage: Message, title: string, preview: string) => {
        const chatId = `chat-${Date.now()}`;
        const newChat: ChatHistoryItem = {
            id: chatId,
            title,
            preview,
            timestamp: new Date(),
        };
        
        setChats(prev => {
            const updated = [newChat, ...prev];
            saveChatsToStorage(updated);
            return updated;
        });
        
        return chatId;
    };

    const deleteChat = async (chatId: string) => {
        setChats(prev => {
            const filtered = prev.filter(chat => chat.id !== chatId);
            saveChatsToStorage(filtered);
            return filtered;
        });
    };

    const updateChatPreview = async (chatId: string, title: string, preview: string) => {
        setChats(prev => {
            const updated = prev.map(chat => 
                chat.id === chatId 
                    ? { ...chat, title, preview, timestamp: new Date() }
                    : chat
            );
            saveChatsToStorage(updated);
            return updated;
        });
    };

    const addMessageToChat = async (chatId: string, message: Message) => {
        // Messages are handled by the chat component, not stored here
        // This is just a stub to maintain API compatibility
        console.log('addMessageToChat called (local storage mode):', chatId);
    };

    const deleteAllChats = async () => {
        setChats([]);
        saveChatsToStorage([]);
    };

    return {
        chats,
        loading,
        createChat,
        deleteChat,
        deleteAllChats,
        updateChatPreview,
        addMessageToChat
    };
}

export function useChatMessages(chatId: string | undefined) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [loadingMessages, setLoadingMessages] = useState(false);

    useEffect(() => {
        if (!chatId) {
            setMessages([]);
            setLoadingMessages(false);
            return;
        }

        // Load messages from localStorage
        setLoadingMessages(true);
        try {
            const stored = localStorage.getItem(`chat-messages-${chatId}`);
            if (stored) {
                const parsed = JSON.parse(stored);
                const msgs = parsed.map((msg: any) => ({
                    ...msg,
                    timestamp: new Date(msg.timestamp),
                })) as Message[];
                setMessages(msgs);
            } else {
                setMessages([]);
            }
        } catch (error) {
            console.error("Error loading messages:", error);
            setMessages([]);
        } finally {
            setLoadingMessages(false);
        }
    }, [chatId]);

    return { messages, loadingMessages };
}
