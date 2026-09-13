// QuizArena Polyphonic Web Audio Engine
// Generates background music loops, tick-tocks, correct chimes, wrong buzzes, and victory fanfare.

class QuizSoundEngine {
    constructor() {
        this.ctx = null;
        this.masterGain = null;
        this.bgGain = null;
        this.sfxGain = null;
        this.isMuted = false;
        this.adminMuted = false;
        this.volume = 0.6;
        this.bgPlaying = false;
        this.bgStep = 0;
        this.bgTimer = null;
        this.unlocked = false;
    }

    init() {
        if (!this.ctx) {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            if (!AudioCtx) return;
            this.ctx = new AudioCtx();

            this.masterGain = this.ctx.createGain();
            this.masterGain.gain.setValueAtTime(this.isMuted || this.adminMuted ? 0.0 : this.volume, this.ctx.currentTime);
            this.masterGain.connect(this.ctx.destination);

            this.bgGain = this.ctx.createGain();
            this.bgGain.gain.setValueAtTime(0.22, this.ctx.currentTime);
            this.bgGain.connect(this.masterGain);

            this.sfxGain = this.ctx.createGain();
            this.sfxGain.gain.setValueAtTime(0.65, this.ctx.currentTime);
            this.sfxGain.connect(this.masterGain);
        }

        if (this.ctx && this.ctx.state === 'suspended') {
            this.ctx.resume();
        }
        this.unlocked = true;
    }

    ensureContext() {
        if (!this.ctx || !this.unlocked) {
            this.init();
        }
        if (this.ctx && this.ctx.state === 'suspended') {
            this.ctx.resume();
        }
    }

    setVolume(val) {
        this.volume = Math.max(0, Math.min(1, val));
        if (this.masterGain && this.ctx && !this.isMuted && !this.adminMuted) {
            this.masterGain.gain.setValueAtTime(this.volume, this.ctx.currentTime);
        }
    }

    toggleMute() {
        this.isMuted = !this.isMuted;
        this.applyMuteState();
        return this.isMuted;
    }

    setMute(state) {
        this.isMuted = Boolean(state);
        this.applyMuteState();
    }

    setAdminMute(muted) {
        this.adminMuted = Boolean(muted);
        this.applyMuteState();
    }

    applyMuteState() {
        if (!this.masterGain || !this.ctx) return;
        const target = (this.isMuted || this.adminMuted) ? 0.0001 : this.volume;
        this.masterGain.gain.setValueAtTime(this.masterGain.gain.value, this.ctx.currentTime);
        this.masterGain.gain.exponentialRampToValueAtTime(target, this.ctx.currentTime + 0.05);
    }

    // ── 1. BACKGROUND MUSIC: UPBEAT GAME SHOW GROOVE ──
    startBgMusic() {
        this.ensureContext();
        if (this.bgPlaying) return;
        this.bgPlaying = true;
        this.bgStep = 0;

        const stepTime = 115;
        const chordRoots = [130.81, 130.81, 130.81, 130.81, 98.00, 98.00, 98.00, 98.00, 110.00, 110.00, 110.00, 110.00, 87.31, 87.31, 87.31, 87.31];
        const melodyPitches = [
            523.25, 659.25, 783.99, 1046.50,
            392.00, 493.88, 587.33, 783.99,
            440.00, 523.25, 659.25, 880.00,
            349.23, 440.00, 523.25, 698.46
        ];

        this.bgTimer = setInterval(() => {
            if (!this.bgPlaying || !this.ctx) return;
            const now = this.ctx.currentTime;
            const idx = this.bgStep % 16;

            if (idx % 2 === 0) {
                const root = chordRoots[idx];
                const oscBass = this.ctx.createOscillator();
                const gainBass = this.ctx.createGain();
                oscBass.type = 'triangle';
                oscBass.frequency.setValueAtTime(root, now);

                gainBass.gain.setValueAtTime(0.35, now);
                gainBass.gain.exponentialRampToValueAtTime(0.001, now + 0.18);

                oscBass.connect(gainBass);
                gainBass.connect(this.bgGain);
                oscBass.start(now);
                oscBass.stop(now + 0.2);
            }

            const pitch = melodyPitches[idx];
            const oscMelody = this.ctx.createOscillator();
            const gainMelody = this.ctx.createGain();
            oscMelody.type = (idx % 4 === 0) ? 'sine' : 'triangle';
            oscMelody.frequency.setValueAtTime(pitch, now);

            gainMelody.gain.setValueAtTime(0.18, now);
            gainMelody.gain.exponentialRampToValueAtTime(0.001, now + 0.1);

            oscMelody.connect(gainMelody);
            gainMelody.connect(this.bgGain);
            oscMelody.start(now);
            oscMelody.stop(now + 0.11);

            if (idx % 2 === 1) {
                const oscHat = this.ctx.createOscillator();
                const gainHat = this.ctx.createGain();
                oscHat.type = 'square';
                oscHat.frequency.setValueAtTime(1400 + (Math.random() * 400), now);
                gainHat.gain.setValueAtTime(0.04, now);
                gainHat.gain.exponentialRampToValueAtTime(0.0001, now + 0.03);
                oscHat.connect(gainHat);
                gainHat.connect(this.bgGain);
                oscHat.start(now);
                oscHat.stop(now + 0.04);
            }

            this.bgStep++;
        }, stepTime);
    }

    stopBgMusic() {
        this.bgPlaying = false;
        if (this.bgTimer) {
            clearInterval(this.bgTimer);
            this.bgTimer = null;
        }
    }

    // ── 2. TICK-TOCK SOUND (<= 5 SECONDS TENSION) ──
    playTick(isLow = false) {
        this.ensureContext();
        if (!this.ctx) return;
        const now = this.ctx.currentTime;

        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        
        const freq = isLow ? 750 : 1100;
        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, now);
        osc.frequency.exponentialRampToValueAtTime(150, now + 0.04);

        gain.gain.setValueAtTime(0.45, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.045);

        osc.connect(gain);
        gain.connect(this.sfxGain);
        osc.start(now);
        osc.stop(now + 0.05);
    }

    // ── 3. CORRECT ANSWER CHIME (DING!) ──
    playCorrect() {
        this.ensureContext();
        if (!this.ctx) return;
        const now = this.ctx.currentTime;

        const notes = [
            { f: 783.99, t: 0.00, dur: 0.25 },
            { f: 1046.50, t: 0.08, dur: 0.35 },
            { f: 1318.51, t: 0.16, dur: 0.60 }
        ];

        notes.forEach(n => {
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(n.f, now + n.t);

            gain.gain.setValueAtTime(0.001, now + n.t);
            gain.gain.linearRampToValueAtTime(0.5, now + n.t + 0.02);
            gain.gain.exponentialRampToValueAtTime(0.001, now + n.t + n.dur);

            osc.connect(gain);
            gain.connect(this.sfxGain);
            osc.start(now + n.t);
            osc.stop(now + n.t + n.dur + 0.05);
        });
    }

    // ── 4. WRONG ANSWER BUZZER ──
    playWrong() {
        this.ensureContext();
        if (!this.ctx) return;
        const now = this.ctx.currentTime;

        [140, 133].forEach(freq => {
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(freq, now);

            gain.gain.setValueAtTime(0.4, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.28);

            osc.connect(gain);
            gain.connect(this.sfxGain);
            osc.start(now);
            osc.stop(now + 0.3);
        });
    }

    // ── 5. VICTORY FANFARE (CHEERFUL CELEBRATION CHORDS & ARPEGGIO) ──
    playFanfare() {
        this.ensureContext();
        if (!this.ctx) return;
        this.stopBgMusic();

        const now = this.ctx.currentTime;

        const melody = [
            { f: 392.00, t: 0.00, dur: 0.15 },
            { f: 523.25, t: 0.16, dur: 0.15 },
            { f: 659.25, t: 0.32, dur: 0.15 },
            { f: 783.99, t: 0.48, dur: 0.35 },
            { f: 659.25, t: 0.88, dur: 0.15 },
            { f: 783.99, t: 1.04, dur: 0.70 }
        ];

        melody.forEach(m => {
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = 'triangle';
            osc.frequency.setValueAtTime(m.f, now + m.t);

            gain.gain.setValueAtTime(0.001, now + m.t);
            gain.gain.linearRampToValueAtTime(0.55, now + m.t + 0.03);
            gain.gain.exponentialRampToValueAtTime(0.001, now + m.t + m.dur);

            osc.connect(gain);
            gain.connect(this.sfxGain);
            osc.start(now + m.t);
            osc.stop(now + m.t + m.dur + 0.05);
        });

        const chordTime = now + 1.1;
        [523.25, 659.25, 783.99, 1046.50].forEach(f => {
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(f, chordTime);

            gain.gain.setValueAtTime(0.001, chordTime);
            gain.gain.linearRampToValueAtTime(0.4, chordTime + 0.04);
            gain.gain.exponentialRampToValueAtTime(0.001, chordTime + 1.6);

            osc.connect(gain);
            gain.connect(this.sfxGain);
            osc.start(chordTime);
            osc.stop(chordTime + 1.7);
        });
    }
}

window.soundEngine = new QuizSoundEngine();

['click', 'touchstart', 'keydown'].forEach(evt => {
    document.addEventListener(evt, () => {
        if (window.soundEngine) {
            window.soundEngine.ensureContext();
        }
    }, { once: false, passive: true });
});
