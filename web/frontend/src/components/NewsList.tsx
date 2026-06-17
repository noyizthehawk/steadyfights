import { useEffect, useState } from "react";
import { getNews } from "../api";
import type { NewsArticle } from "../api";

// Fetches news for one fighter. Mounted only when the News tab is open, so the
// newsAPI call doesn't fire until the user actually wants it. efficient design choice
export function NewsList({ fighter }: { fighter: string }) {
    const [articles, setArticles] = useState<NewsArticle[] | null>(null);
    const [error, setError] = useState<string>("");

    useEffect(() => {
        setArticles(null);
        setError("");
        getNews(fighter)
            .then(setArticles)
            .catch((e) => setError(e instanceof Error ? e.message : "Failed to load news"));
    }, [fighter]);

    if (error) return <p className="error">{error}</p>;
    if (!articles) return <p className="news-empty">Loading news…</p>;
    if (articles.length === 0) return <p className="news-empty">No recent news for {fighter}.</p>;

    return (
        <ul className="news-list">
            {articles.map((a) => (
                <li key={a.url} className="news-item">
                    <a href={a.url} target="_blank" rel="noopener noreferrer" className="news-link">
                        {a.image && (
                            <img
                                className="news-thumb"
                                src={a.image}
                                alt=""
                                loading="lazy"
                                onError={(e) => { e.currentTarget.style.display = "none"; }}
                            />
                        )}
                        <div className="news-text">
                            <span className="news-title">{a.title}</span>
                            <span className="news-meta">
                                {a.source}
                                {a.published_at && ` · ${new Date(a.published_at).toLocaleDateString()}`}
                            </span>
                        </div>
                    </a>
                </li>
            ))}
        </ul>
    );
}
