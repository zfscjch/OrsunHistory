class MessageChannel {
    constructor(name) {
        this.channel = new BroadcastChannel(name);
        this.handlers = new Map();
    }

    on(eventType, callback) {
        if (!this.handlers.has(eventType)) {
            this.handlers.set(eventType, []);
        }
        this.handlers.get(eventType).push(callback);
    }

    off(eventType, callback) {
        if (this.handlers.has(eventType)) {
            const list = this.handlers.get(eventType).filter(fn => fn !== callback);
            this.handlers.set(eventType, list);
        }
    }

    emit(eventType, payload) {
        this.channel.postMessage({ eventType, payload });
    }

    close() {
        this.channel.close();
    }
}