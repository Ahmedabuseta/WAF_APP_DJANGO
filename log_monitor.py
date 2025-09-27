#!/usr/bin/env python3
"""
WAF Log Monitor
Real-time log monitoring tool for debugging WAF behavior
"""

import time
import os
import sys
import argparse
from datetime import datetime

def tail_file(filename, lines=10):
    """Tail a file like tail -f"""
    if not os.path.exists(filename):
        print(f"⚠️  Log file {filename} doesn't exist yet")
        return
        
    with open(filename, 'r') as f:
        # Go to end of file
        f.seek(0, 2)
        
        # Print last few lines
        f.seek(0, 0)
        file_lines = f.readlines()
        for line in file_lines[-lines:]:
            print(line.rstrip())
        
        # Follow the file
        while True:
            line = f.readline()
            if line:
                print(line.rstrip())
            else:
                time.sleep(0.1)

def monitor_multiple_logs():
    """Monitor multiple log files simultaneously"""
    import threading
    import queue
    
    log_files = {
        'WAF': 'waf_debug.log',
        'PROXY': 'waf_proxy.log'
    }
    
    def tail_log(name, filename, q):
        if not os.path.exists(filename):
            q.put(f"⚠️  [{name}] Log file {filename} doesn't exist yet")
            return
            
        with open(filename, 'r') as f:
            f.seek(0, 2)  # Go to end
            while True:
                line = f.readline()
                if line:
                    q.put(f"[{name}] {line.rstrip()}")
                else:
                    time.sleep(0.1)
    
    # Create queue for log messages
    log_queue = queue.Queue()
    
    # Start threads for each log file
    threads = []
    for name, filename in log_files.items():
        thread = threading.Thread(target=tail_log, args=(name, filename, log_queue))
        thread.daemon = True
        thread.start()
        threads.append(thread)
    
    print("🔍 Monitoring WAF logs (Ctrl+C to stop)")
    print("=" * 60)
    
    try:
        while True:
            try:
                message = log_queue.get(timeout=1)
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"{timestamp} {message}")
            except queue.Empty:
                continue
    except KeyboardInterrupt:
        print("\n👋 Stopping log monitor")

def main():
    parser = argparse.ArgumentParser(description='WAF Log Monitor')
    parser.add_argument('--file', '-f', help='Monitor specific log file')
    parser.add_argument('--lines', '-n', type=int, default=10, help='Number of initial lines to show')
    parser.add_argument('--multiple', '-m', action='store_true', help='Monitor multiple log files')
    
    args = parser.parse_args()
    
    if args.multiple:
        monitor_multiple_logs()
    elif args.file:
        print(f"🔍 Monitoring {args.file} (Ctrl+C to stop)")
        print("=" * 50)
        tail_file(args.file, args.lines)
    else:
        print("WAF Log Monitor")
        print("==============")
        print()
        print("Available options:")
        print("  -f waf_debug.log    Monitor WAF middleware logs")
        print("  -f waf_proxy.log    Monitor proxy middleware logs")
        print("  -m                  Monitor all logs simultaneously")
        print()
        print("Examples:")
        print("  python log_monitor.py -f waf_debug.log")
        print("  python log_monitor.py -m")

if __name__ == '__main__':
    main()