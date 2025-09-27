/**
 * Video Fallback Animation
 * Creates an animated background when video files are not available
 */

class SecurityAnimation {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.particles = [];
        this.animationId = null;
        
        this.resize();
        this.init();
        this.animate();
        
        window.addEventListener('resize', () => this.resize());
    }
    
    resize() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    }
    
    init() {
        // Create particles for security-themed animation
        for (let i = 0; i < 50; i++) {
            this.particles.push({
                x: Math.random() * this.canvas.width,
                y: Math.random() * this.canvas.height,
                vx: (Math.random() - 0.5) * 2,
                vy: (Math.random() - 0.5) * 2,
                radius: Math.random() * 3 + 1,
                opacity: Math.random() * 0.5 + 0.2,
                color: this.getRandomColor()
            });
        }
    }
    
    getRandomColor() {
        const colors = ['#ff6b6b', '#ee5a52', '#667eea', '#764ba2', '#feca57'];
        return colors[Math.floor(Math.random() * colors.length)];
    }
    
    drawParticle(particle) {
        this.ctx.save();
        this.ctx.globalAlpha = particle.opacity;
        this.ctx.fillStyle = particle.color;
        this.ctx.beginPath();
        this.ctx.arc(particle.x, particle.y, particle.radius, 0, Math.PI * 2);
        this.ctx.fill();
        this.ctx.restore();
    }
    
    updateParticle(particle) {
        particle.x += particle.vx;
        particle.y += particle.vy;
        
        // Wrap around edges
        if (particle.x < 0) particle.x = this.canvas.width;
        if (particle.x > this.canvas.width) particle.x = 0;
        if (particle.y < 0) particle.y = this.canvas.height;
        if (particle.y > this.canvas.height) particle.y = 0;
        
        // Pulse opacity
        particle.opacity += Math.sin(Date.now() * 0.001 + particle.x * 0.01) * 0.01;
        particle.opacity = Math.max(0.1, Math.min(0.8, particle.opacity));
    }
    
    drawConnections() {
        this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
        this.ctx.lineWidth = 1;
        
        for (let i = 0; i < this.particles.length; i++) {
            for (let j = i + 1; j < this.particles.length; j++) {
                const dx = this.particles[i].x - this.particles[j].x;
                const dy = this.particles[i].y - this.particles[j].y;
                const distance = Math.sqrt(dx * dx + dy * dy);
                
                if (distance < 100) {
                    this.ctx.save();
                    this.ctx.globalAlpha = (100 - distance) / 100 * 0.5;
                    this.ctx.beginPath();
                    this.ctx.moveTo(this.particles[i].x, this.particles[i].y);
                    this.ctx.lineTo(this.particles[j].x, this.particles[j].y);
                    this.ctx.stroke();
                    this.ctx.restore();
                }
            }
        }
    }
    
    animate() {
        // Clear canvas with gradient background
        const gradient = this.ctx.createLinearGradient(0, 0, this.canvas.width, this.canvas.height);
        gradient.addColorStop(0, 'rgba(255, 107, 107, 0.1)');
        gradient.addColorStop(0.5, 'rgba(238, 90, 82, 0.1)');
        gradient.addColorStop(1, 'rgba(102, 126, 234, 0.1)');
        
        this.ctx.fillStyle = gradient;
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Update and draw particles
        this.particles.forEach(particle => {
            this.updateParticle(particle);
            this.drawParticle(particle);
        });
        
        // Draw connections between nearby particles
        this.drawConnections();
        
        // Draw security-themed overlay text
        this.drawSecurityOverlay();
        
        this.animationId = requestAnimationFrame(() => this.animate());
    }
    
    drawSecurityOverlay() {
        const time = Date.now() * 0.001;
        
        // Draw "SECURITY" text with fade effect
        this.ctx.save();
        this.ctx.fillStyle = `rgba(255, 255, 255, ${0.1 + Math.sin(time) * 0.05})`;
        this.ctx.font = 'bold 120px Arial';
        this.ctx.textAlign = 'center';
        this.ctx.fillText('SECURITY', this.canvas.width / 2, this.canvas.height / 2);
        this.ctx.restore();
        
        // Draw scanning line effect
        const scanY = (Math.sin(time * 2) * 0.5 + 0.5) * this.canvas.height;
        this.ctx.save();
        this.ctx.strokeStyle = 'rgba(255, 107, 107, 0.8)';
        this.ctx.lineWidth = 2;
        this.ctx.beginPath();
        this.ctx.moveTo(0, scanY);
        this.ctx.lineTo(this.canvas.width, scanY);
        this.ctx.stroke();
        this.ctx.restore();
    }
    
    destroy() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
    }
}

// Initialize animation when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Only create fallback animation if video fails to load
    const video = document.getElementById('securityVideo');
    
    if (video) {
        video.addEventListener('error', createFallbackAnimation);
        video.addEventListener('abort', createFallbackAnimation);
        
        // Check if video actually loads
        setTimeout(() => {
            if (video.readyState === 0) {
                createFallbackAnimation();
            }
        }, 3000);
    } else {
        createFallbackAnimation();
    }
    
    function createFallbackAnimation() {
        // Create canvas for fallback animation
        const canvas = document.createElement('canvas');
        canvas.id = 'securityCanvas';
        canvas.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
            pointer-events: none;
        `;
        
        // Replace video background with canvas
        const videoBackground = document.querySelector('.video-background');
        if (videoBackground) {
            videoBackground.innerHTML = '';
            videoBackground.appendChild(canvas);
            
            // Start animation
            new SecurityAnimation('securityCanvas');
        }
    }
});