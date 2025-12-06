import React from 'react';
import { motion } from 'framer-motion';

// Helper to determine status badge styling
const getStatusInfo = (status, deadline) => {
    // If status is explicitly provided, use it
    if (status) {
        const s = status.toLowerCase();
        if (s === 'expired') return { label: 'Expired', className: 'status-expired' };
        if (s === 'expiring') return { label: 'Expires Soon', className: 'status-expiring' };
        if (s === 'active') return { label: 'Active', className: 'status-active' };
    }

    // Otherwise try to determine from deadline
    if (deadline) {
        try {
            const deadlineDate = new Date(deadline);
            const now = new Date();
            const daysLeft = Math.ceil((deadlineDate - now) / (1000 * 60 * 60 * 24));

            if (daysLeft < 0) return { label: 'Expired', className: 'status-expired' };
            if (daysLeft <= 7) return { label: 'Expires Soon', className: 'status-expiring' };
            return { label: 'Active', className: 'status-active' };
        } catch (e) {
            return { label: 'Active', className: 'status-active' };
        }
    }

    return { label: 'Active', className: 'status-active' };
};

// Calendar icon component
const CalendarIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
        <line x1="16" y1="2" x2="16" y2="6"></line>
        <line x1="8" y1="2" x2="8" y2="6"></line>
        <line x1="3" y1="10" x2="21" y2="10"></line>
    </svg>
);

// Document icon component
const DocumentIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
        <polyline points="14 2 14 8 20 8"></polyline>
    </svg>
);

const TenderCard = ({ tenders }) => {
    if (!tenders || tenders.length === 0) return null;

    return (
        <div className="tender-cards-container">
            {tenders.map((tender, index) => {
                const statusInfo = getStatusInfo(tender.status, tender.deadline);

                return (
                    <motion.div
                        key={index}
                        className="tender-card"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.08, duration: 0.3 }}
                    >
                        {/* Card Header */}
                        <div className="tender-card-header">
                            <h3 className="tender-card-title">{tender.title}</h3>
                            <span className={`tender-status-badge ${statusInfo.className}`}>
                                {statusInfo.label}
                            </span>
                        </div>

                        {/* Deadline */}
                        {tender.deadline && (
                            <div className="tender-deadline">
                                <CalendarIcon />
                                <span>{tender.deadline}</span>
                            </div>
                        )}

                        {/* Description */}
                        {tender.description && (
                            <p className="tender-card-description">{tender.description}</p>
                        )}

                        {/* Documents Section */}
                        {tender.documents && tender.documents.length > 0 && (
                            <div className="tender-docs-section">
                                <div className="tender-docs-header">
                                    <DocumentIcon />
                                    <span>Documents</span>
                                </div>
                                <div className="tender-docs-chips">
                                    {tender.documents.map((doc, i) => (
                                        <a
                                            key={i}
                                            href={doc.url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="tender-doc-chip"
                                        >
                                            <DocumentIcon />
                                            <span>{doc.title || `Document ${i + 1}`}</span>
                                        </a>
                                    ))}
                                </div>
                            </div>
                        )}
                    </motion.div>
                );
            })}
        </div>
    );
};

export default TenderCard;
