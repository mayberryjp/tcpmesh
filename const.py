
VERSION="v1.0.2"
ENTITIES = {
    "measurement": {"state_class": "measurement", "unit_of_measurement": "ms", "device_class": None},
    "connectivity": {"device_class": "connectivity",  "unit_of_measurement": None, "state_class": None}
}

# Add to const.py
ENTITIES = {
    "measurement": {
        "device_class": None,
        "unit_of_measurement": "ms",
        "state_class": "measurement"
    },
    "connectivity": {
        "device_class": "connectivity",
        "unit_of_measurement": None,
        "state_class": None
    },
    "counter": {  # Add this new entry
        "device_class": None,
        "unit_of_measurement": "count",
        "state_class": "total_increasing"
    }
}

prompt_response_dict = {
    "P001_tech_What is the current status of the system? Please provide a detailed report including all subsystems, recent incidents, uptime metrics for the last 30 days, and any scheduled maintenance that might impact operations. We need this for the quarterly review meeting scheduled for tomorrow.": "R001_tech_All systems operational with 99.99% uptime over the last 24 hours. Core services running optimally with no reported errors in the last 72 hours. Backend database connections stable with average query time of 47ms. CDN performance at expected levels with global availability. Backup systems verified and operational. No scheduled maintenance in the next 48 hours.",
    
    "P002_weather_How's the forecast looking for tomorrow?": "R002_weather_Expect partly cloudy conditions with temperatures ranging between 18°C and 25°C. Morning fog will clear by 9 AM, giving way to sunshine until mid-afternoon when cloud cover will increase to approximately 60%. Humidity levels will remain moderate at 45-55%. Wind speeds will be light at 5-10 km/h from the southwest. No precipitation is expected, making it ideal for outdoor activities. UV index will be moderate at 4-5, so sun protection is still advised during peak hours.",
    
    "P003_network_Ping status report requested for all critical infrastructure nodes in datacenter Alpha-7, including east and west coast CDN endpoints, database clusters, authentication services, and primary/secondary DNS. Please include packet loss statistics, round trip times, jitter measurements, and any anomalies detected in the last monitoring window." + "A" * 3000: "R003_network_Network latency at 23ms, packet loss at 0.1%, bandwidth at 98.7% of capacity. All monitored endpoints responding within expected parameters. East coast CDN showing slightly elevated response times (27ms vs baseline 22ms) due to scheduled maintenance on edge nodes EC-7 through EC-12. West coast services operating normally. Database cluster connections stable across all shards. Authentication services operating with 99.999% availability since last restart 47 days ago." + "B" * 500,
    
    "P004_security_" + "X" * 100: "R004_security_Authentication protocol alpha initiated. Token verification complete. All security parameters validated and access granted to requested resources. Multi-factor authentication successful across all verification channels. Session established with standard timeout parameters. Activity logging enabled per security policy requirements. No anomalies detected in the authentication flow." + "Y" * 2000,
    
    "P005_database_What's the current transaction load? Please provide details on read/write ratios, query optimization opportunities, cache hit rates, and any blocking operations that may be affecting overall system performance. Are there any recommendations for improving current database operation efficiency?" + "C" * 1500: "R005_database_Processing 4,392 transactions per second with an average response time of 47ms. Current read/write ratio is 78/22 with optimal indexing on primary query paths. Cache hit rate is 94.7% for frequently accessed data. No significant blocking operations detected. Two long-running analytical queries have been isolated to dedicated replicas to prevent impact on transactional performance. Recent optimization of the customer profile query pattern has reduced execution time by 37%.",
    
    "P006_memory_Status of memory allocation?" + "D" * 50: "R006_memory_Currently at 42% capacity with 3.7GB free. No memory leaks detected. Heap fragmentation at 3% which is within acceptable parameters. Garbage collection running on standard intervals with no excessive pauses. Memory-intensive processes have been properly contained within their allocated boundaries. Swap usage is minimal at 0.1%. All memory-intensive operations are proceeding with expected consumption patterns." + "E" * 1200,
    
    "P007_power_Is the backup system engaged and ready? Have all UPS units been tested according to the quarterly maintenance schedule? What is the current load on the primary and secondary power distribution units? Are all cooling systems receiving adequate power to maintain optimal temperature ranges in all server rooms?" + "F" * 500: "R007_power_Backup power systems on standby. Main power stable at 99.8% efficiency. All UPS units tested last week with 100% pass rate. Backup generators successfully load-tested for 24-hour continuous operation. Power distribution units operating at 37% capacity with balanced load across all phases. No anomalies detected in power quality monitoring. Emergency shutdown protocols verified and operational.",
    
    "P008_cooling_Temperature check requested for all server rooms, with particular attention to high-density rack areas in zones 3 and 4. Please confirm proper operation of all CRAC units, chilled water systems, and airflow management components. Have there been any thermal events or threshold warnings in the past 24 hours?" + "G" * 2000: "R008_cooling_" + "H" * 4000,
    
    "P009_traffic_" + "I" * 4500: "R009_traffic_Inbound at 5.7Gbps, outbound at 3.2Gbps with normal traffic patterns observed. Peak utilization reached 82% of capacity at 14:30 but quickly normalized. Traffic distribution across regions shows expected patterns with APAC traffic increasing 7% week-over-week. Content delivery optimized with 94% edge cache hit rate. DDoS protection active with no mitigations required in the past 72 hours. All traffic encryption protocols operating normally." + "J" * 200,
    
    "P010_storage_Remaining capacity report for all storage tiers including SAN, NAS, and object storage platforms. Include growth projections based on current utilization trends and highlight any storage pools that may require expansion in the next 90 days. Are all backup and archival processes completing within their designated windows?": "R010_storage_Primary storage at 63% capacity. Backup storage at 47%. Redundancy systems intact. SSD arrays operating at optimal performance with wear leveling functioning as expected. Projected to reach 75% capacity in approximately 47 days based on current growth patterns. Archival systems processed 2.3TB of data in the last backup window with no errors. Deduplication ratio improved to 4.7:1 after recent algorithm updates. Storage tiering policy has successfully migrated 17TB of infrequently accessed data to lower-cost storage, improving overall system economics while maintaining accessibility requirements." + "K" * 3000,
    
    # Continue with the rest of the entries, some with short prompts and long responses,
    # others with long prompts and short responses, etc.
    "P011_processor_Current CPU utilization across all production clusters? Please include per-core metrics, process distribution, and any thermal throttling events." + "L" * 100: "R011_processor_Average CPU load at 37% across all cores. No bottlenecks detected. Process distribution is optimal with high-priority tasks receiving appropriate scheduling priority. No thermal events detected in the monitoring period. Virtualization overhead measured at 2.3% which is within expected parameters. CPU cache hit rates at 97.8% indicating efficient code execution paths." + "M" * 500,
    
    # Entry with exact 50 character prompt
    "P012_firewall_Security perimeter status?" + "X" * 20: "R012_firewall_Firewall actively blocking 427 threats. All security rules properly enforced. Intrusion detection system has logged 37 potential reconnaissance attempts, all of which were successfully mitigated. Web application firewall has processed 1.7 million requests with 99.98% legitimate traffic passing without added latency. Rule optimization last week improved processing efficiency by 7.3% while maintaining security posture. All signature databases updated within the last hour." + "N" * 2000,
    
    # Entry with exact 5000 character response
    "P013_backup_When was the last backup completed? Has it been verified? Are there any issues with the retention policy implementation?" + "O" * 300: "R013_backup_" + "P" * 4922,
    
    # Many more entries with varying lengths...
    "P099_history_Historical document preservation status? What are the current environmental conditions in the main archive facility? Have there been any deviations from optimal temperature or humidity levels in the past month? What is the status of the ongoing digitization project for pre-1900 manuscripts?" + "Q" * 1500: "R099_history_Archive environment maintained at 18°C and 45% humidity. Digitization proceeding according to schedule with 37% of targeted materials now preserved in digital format. Climate control systems operating within parameters. Recent inspection found no evidence of mold or pests in the storage facilities. Specialized document scanning for deteriorating materials has been prioritized and is 78% complete. Metadata tagging project is slightly behind schedule at 72% completion versus target of 80%." + "R" * 1000,
    
    # Entry with exact 5000 character prompt
    "P100_mathematics_" + "S" * 4970: "R100_mathematics_Proof verification system operational. Computing resources optimized for parallel theorem proving. Algorithm efficiency improved by 23% after implementation of new heuristic approaches. Formal verification of critical security protocols completed with no detected flaws. Mathematical model simulations running at expected performance levels. Cryptographic algorithm testing proceeding according to schedule with all test vectors processing successfully." + "T" * 3500
}