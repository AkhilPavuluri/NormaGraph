// Reference build: feedback is stored in localStorage only (no backend persistence).

import { devLog } from './devLog'

export interface FeedbackData {
    question: string;
    response: string;
    type: 'up' | 'down';
    comment?: string;
    messageId?: string;
    timestamp?: any;
}

/**
 * Submits user feedback to local storage (backend connection removed).
 */
export const submitFeedback = async (data: FeedbackData) => {
    try {
        // Store feedback in local storage instead of Firestore
        const feedbacks = JSON.parse(localStorage.getItem('feedbacks') || '[]');
        feedbacks.push({
            ...data,
            timestamp: new Date().toISOString(),
        });
        localStorage.setItem('feedbacks', JSON.stringify(feedbacks));
        
        devLog('Feedback saved locally:', data)
        return { success: true };
    } catch (error) {
        console.error('Error submitting feedback:', error);
        return { success: false, error };
    }
};
