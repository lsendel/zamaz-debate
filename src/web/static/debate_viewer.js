/**
 * Enhanced Debate Viewer Component
 * Provides a clean, organized view of debate details
 */

class DebateViewer {
    constructor() {
        this.currentDebate = null;
    }

    /**
     * Format and display debate details
     */
    async displayDebate(debateId) {
        try {
            const response = await fetch(`/debates/${debateId}`);
            if (!response.ok) throw new Error('Failed to load debate');
            
            this.currentDebate = await response.json();
            return this.renderDebate();
        } catch (error) {
            console.error('Error loading debate:', error);
            return this.renderError(error.message);
        }
    }

    /**
     * Render the debate in a structured format
     */
    renderDebate() {
        const debate = this.currentDebate;
        const consensus = debate.consensus || {};
        
        return `
            <div class="debate-viewer">
                ${this.renderHeader(debate)}
                ${this.renderConsensusSection(consensus)}
                ${this.renderArgumentsSection(debate.rounds)}
                ${this.renderDecisionSection(debate.final_decision)}
                ${this.renderMetadata(debate)}
            </div>
        `;
    }

    /**
     * Render debate header
     */
    renderHeader(debate) {
        return `
            <div class="debate-header">
                <h2>Debate Analysis</h2>
                <div class="debate-question">
                    <h3>Question</h3>
                    <p>${this.escapeHtml(debate.question)}</p>
                </div>
                ${debate.context ? `
                    <div class="debate-context">
                        <h3>Context</h3>
                        <p>${this.escapeHtml(debate.context)}</p>
                    </div>
                ` : ''}
            </div>
        `;
    }

    /**
     * Render consensus analysis section
     */
    renderConsensusSection(consensus) {
        if (!consensus.level && consensus.level !== 0) {
            return '';
        }

        const levelClass = this.getConsensusLevelClass(consensus.level);
        const levelPercent = (consensus.level * 100).toFixed(0);

        return `
            <div class="consensus-section">
                <h3>Consensus Analysis</h3>
                <div class="consensus-overview">
                    <div class="consensus-meter">
                        <div class="consensus-level ${levelClass}" style="width: ${levelPercent}%">
                            <span>${levelPercent}%</span>
                        </div>
                    </div>
                    <div class="consensus-type">
                        Consensus Type: <strong>${consensus.type || 'Unknown'}</strong>
                    </div>
                </div>

                ${consensus.areas_of_agreement && consensus.areas_of_agreement.length > 0 ? `
                    <div class="agreement-section">
                        <h4><i class="fas fa-handshake"></i> Areas of Agreement</h4>
                        <ul>
                            ${consensus.areas_of_agreement.map(area => 
                                `<li>${this.escapeHtml(area)}</li>`
                            ).join('')}
                        </ul>
                    </div>
                ` : ''}

                ${consensus.areas_of_disagreement && consensus.areas_of_disagreement.length > 0 ? `
                    <div class="disagreement-section">
                        <h4><i class="fas fa-exclamation-triangle"></i> Areas of Disagreement</h4>
                        <ul>
                            ${consensus.areas_of_disagreement.map(area => 
                                `<li>${this.escapeHtml(area)}</li>`
                            ).join('')}
                        </ul>
                    </div>
                ` : ''}

                ${consensus.combined_recommendation ? `
                    <div class="recommendation-section">
                        <h4><i class="fas fa-lightbulb"></i> Combined Recommendation</h4>
                        <p>${this.escapeHtml(consensus.combined_recommendation)}</p>
                    </div>
                ` : ''}
            </div>
        `;
    }

    /**
     * Render arguments from each participant
     */
    renderArgumentsSection(rounds) {
        if (!rounds || rounds.length === 0) {
            return '';
        }

        return `
            <div class="arguments-section">
                <h3>Debate Arguments</h3>
                ${rounds.map((round, index) => `
                    <div class="debate-round">
                        <h4>Round ${round.round || index + 1}</h4>
                        <div class="arguments-grid">
                            <div class="claude-argument">
                                <div class="participant-header">
                                    <i class="fas fa-brain"></i> Claude's Analysis
                                </div>
                                <div class="argument-content">
                                    ${this.formatArgument(round.claude)}
                                </div>
                            </div>
                            <div class="gemini-argument">
                                <div class="participant-header">
                                    <i class="fas fa-gem"></i> Gemini's Analysis
                                </div>
                                <div class="argument-content">
                                    ${this.formatArgument(round.gemini)}
                                </div>
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    /**
     * Format argument text for better readability
     */
    formatArgument(text) {
        if (!text) return '<p>No argument provided</p>';

        // Escape HTML first
        text = this.escapeHtml(text);

        // Convert numbered lists
        text = text.replace(/(\d+)\.\s+(.+?)(?=\n\d+\.|\n\n|$)/g, '<li>$2</li>');
        text = text.replace(/(<li>.*<\/li>)/s, '<ol>$1</ol>');

        // Convert bullet points
        text = text.replace(/[-•]\s+(.+?)(?=\n[-•]|\n\n|$)/g, '<li>$1</li>');
        text = text.replace(/(<li>.*<\/li>)(?!.*<\/ol>)/s, '<ul>$1</ul>');

        // Convert paragraphs
        text = text.split('\n\n').map(para => {
            if (para.trim() && !para.includes('<ol>') && !para.includes('<ul>')) {
                return `<p>${para.trim()}</p>`;
            }
            return para;
        }).join('');

        // Highlight key phrases
        text = text.replace(/\b(recommend|should|must|critical|important|concern|risk)\b/gi, 
            '<span class="highlight">$1</span>');

        return text;
    }

    /**
     * Render the final decision section
     */
    renderDecisionSection(decision) {
        if (!decision) return '';

        // Extract just the consensus analysis if present
        const consensusMatch = decision.match(/Consensus Analysis:([\s\S]*?)$/);
        if (consensusMatch) {
            // Don't show the raw decision text since we're showing structured consensus
            return '';
        }

        // Otherwise show the decision
        return `
            <div class="decision-section">
                <h3>Final Decision</h3>
                <div class="decision-content">
                    ${this.formatArgument(decision)}
                </div>
            </div>
        `;
    }

    /**
     * Render metadata section
     */
    renderMetadata(debate) {
        const startTime = new Date(debate.start_time);
        const endTime = new Date(debate.end_time);
        const duration = Math.round((endTime - startTime) / 1000);

        return `
            <div class="metadata-section">
                <h4>Debate Information</h4>
                <div class="metadata-grid">
                    <div class="metadata-item">
                        <span class="label">Debate ID:</span>
                        <span class="value">${debate.id}</span>
                    </div>
                    <div class="metadata-item">
                        <span class="label">Complexity:</span>
                        <span class="value complexity-${debate.complexity}">${debate.complexity}</span>
                    </div>
                    <div class="metadata-item">
                        <span class="label">Duration:</span>
                        <span class="value">${duration}s</span>
                    </div>
                    <div class="metadata-item">
                        <span class="label">Date:</span>
                        <span class="value">${startTime.toLocaleString()}</span>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Get CSS class based on consensus level
     */
    getConsensusLevelClass(level) {
        if (level >= 0.8) return 'consensus-high';
        if (level >= 0.5) return 'consensus-medium';
        return 'consensus-low';
    }

    /**
     * Render error message
     */
    renderError(message) {
        return `
            <div class="debate-viewer error">
                <div class="error-message">
                    <i class="fas fa-exclamation-circle"></i>
                    <p>Error: ${this.escapeHtml(message)}</p>
                </div>
            </div>
        `;
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Export for use in other modules
window.DebateViewer = DebateViewer;