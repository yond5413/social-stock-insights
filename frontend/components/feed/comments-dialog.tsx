"use client"

import { useState, useEffect } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { ScrollArea } from "@/components/ui/scroll-area"
import { MessageSquare, Send, Loader2 } from "lucide-react"
import { useApi } from "@/hooks/useApi"
import { useAuth } from "@/contexts/AuthContext"
import { formatDistanceToNow } from "date-fns"

interface Comment {
    id: string
    user_id: string
    username: string
    content: string
    created_at: string
}

interface CommentsDialogProps {
    postId: string
    commentCount: number
    onCommentAdded?: () => void
}

export function CommentsDialog({ postId, commentCount, onCommentAdded }: CommentsDialogProps) {
    const [open, setOpen] = useState(false)
    const [comments, setComments] = useState<Comment[]>([])
    const [newComment, setNewComment] = useState("")
    const [loading, setLoading] = useState(false)
    const [submitting, setSubmitting] = useState(false)
    const { apiRequest } = useApi()
    const { user } = useAuth()

    useEffect(() => {
        if (open) {
            fetchComments()
        }
    }, [open, postId])

    const fetchComments = async () => {
        setLoading(true)
        try {
            const data = await apiRequest<Comment[]>(`/posts/${postId}/comments`)
            setComments(data)
        } catch (error) {
            console.error("Failed to fetch comments:", error)
        } finally {
            setLoading(false)
        }
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!newComment.trim()) return

        setSubmitting(true)
        try {
            const comment = await apiRequest<Comment>(`/posts/${postId}/comment`, {
                method: "POST",
                body: JSON.stringify({ content: newComment }),
            })

            // Optimistically add comment or re-fetch
            // Since the API returns the comment object but maybe not username immediately if not joined
            // We'll just re-fetch to be safe and simple for now, or manually append
            setNewComment("")
            fetchComments()
            if (onCommentAdded) onCommentAdded()
        } catch (error) {
            console.error("Failed to post comment:", error)
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button variant="ghost" size="sm" className="flex-1 gap-2 hover:text-blue-600 hover:bg-blue-500/10 transition-colors">
                    <MessageSquare className="h-4 w-4" />
                    <span className="text-xs font-medium">
                        {commentCount > 0 ? commentCount : "Comment"}
                    </span>
                </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[500px] h-[600px] flex flex-col">
                <DialogHeader>
                    <DialogTitle>Comments</DialogTitle>
                </DialogHeader>

                <ScrollArea className="flex-1 pr-4 -mr-4">
                    {loading ? (
                        <div className="flex justify-center p-8">
                            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                        </div>
                    ) : comments.length === 0 ? (
                        <div className="text-center py-12 text-muted-foreground">
                            No comments yet. Be the first to share your thoughts!
                        </div>
                    ) : (
                        <div className="space-y-4 py-4">
                            {comments.map((comment) => (
                                <div key={comment.id} className="flex gap-3">
                                    <Avatar className="h-8 w-8">
                                        <AvatarImage src={`https://avatar.vercel.sh/${comment.user_id}`} />
                                        <AvatarFallback>{comment.username.slice(0, 2).toUpperCase()}</AvatarFallback>
                                    </Avatar>
                                    <div className="flex-1 space-y-1">
                                        <div className="flex items-center gap-2">
                                            <span className="text-sm font-semibold">{comment.username}</span>
                                            <span className="text-xs text-muted-foreground">
                                                {formatDistanceToNow(new Date(comment.created_at), { addSuffix: true })}
                                            </span>
                                        </div>
                                        <p className="text-sm text-foreground/90">{comment.content}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </ScrollArea>

                <div className="pt-4 mt-auto border-t">
                    <form onSubmit={handleSubmit} className="flex gap-2">
                        <Textarea
                            placeholder="Write a comment..."
                            value={newComment}
                            onChange={(e) => setNewComment(e.target.value)}
                            className="min-h-[40px] max-h-[100px] resize-none"
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault()
                                    handleSubmit(e)
                                }
                            }}
                        />
                        <Button type="submit" size="icon" disabled={submitting || !newComment.trim()}>
                            {submitting ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                                <Send className="h-4 w-4" />
                            )}
                        </Button>
                    </form>
                </div>
            </DialogContent>
        </Dialog>
    )
}
