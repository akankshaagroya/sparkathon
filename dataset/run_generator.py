#!/usr/bin/env python3
"""
Sample script to run the Cold Chain Dataset Generator
This demonstrates how to use the generator and produces sample output
"""

import os
import sys
from generate_dataset import ColdChainDataGenerator

def main():
    """Run the dataset generator with sample configuration"""
    
    print("="*60)
    print("Cold Chain Logistics Dataset Generator")
    print("="*60)
    
    # Create generator instance
    generator = ColdChainDataGenerator()
    
    # Generate the complete dataset
    try:
        generator.generate_dataset()
        
        # Print file information
        output_dir = generator.CONFIG["output_dir"]
        print(f"\n📁 Generated files in '{output_dir}' directory:")
        
        for filename in ["trucks_metadata.csv", "events.csv", "batches.csv", 
                        "complete_dataset.json", "trucks_metadata.json", "events.json"]:
            filepath = os.path.join(output_dir, filename)
            if os.path.exists(filepath):
                size = os.path.getsize(filepath)
                print(f"  📄 {filename}: {size:,} bytes")
        
        print("\n✅ Dataset generation completed successfully!")
        print("\n💡 Next steps:")
        print("   1. Check the 'output' directory for generated files")
        print("   2. Run 'python realtime_simulator.py' for real-time simulation")
        print("   3. Edit 'config.py' to customize settings")
        
    except Exception as e:
        print(f"❌ Error generating dataset: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 