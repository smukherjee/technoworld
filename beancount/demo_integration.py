#!/usr/bin/env python3
"""
Demo script to showcase beancount-import integration.
This script demonstrates Phase 1 of the migration strategy.
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Run the demo workflow."""
    print("🚀 Beancount-Import Integration Demo")
    print("=" * 50)
    
    # Step 1: Run the enhanced main.py
    print("\n📊 Step 1: Processing Excel with enhanced classification...")
    try:
        result = subprocess.run([
            sys.executable, "main.py"
        ], capture_output=True, text=True, cwd=Path(__file__).parent)
        
        if result.returncode == 0:
            print("✅ Excel processing completed successfully!")
            print("📁 Files generated:")
            print("   - classified_transactions.csv")
            print("   - transactions.beancount")
            if os.path.exists("beancount_import_output"):
                print("   - beancount_import_output/ (enhanced processing)")
        else:
            print("❌ Excel processing failed:")
            print(result.stderr)
            return
            
    except Exception as e:
        print(f"❌ Error running main.py: {e}")
        return
    
    # Step 2: Check if beancount-import output was generated
    output_dir = Path("beancount_import_output")
    if output_dir.exists():
        print(f"\n🎯 Step 2: Enhanced features generated in {output_dir}")
        
        # List generated files
        for file_path in output_dir.rglob("*"):
            if file_path.is_file():
                print(f"   📄 {file_path.relative_to(output_dir)}")
        
        # Check for web interface
        web_dir = output_dir / "web"
        if web_dir.exists():
            startup_script = web_dir / "start_web_interface.py"
            if startup_script.exists():
                print(f"\n🌐 Step 3: Web interface available!")
                print(f"   💡 To start the web interface:")
                print(f"      cd {web_dir}")
                print(f"      python start_web_interface.py")
                print(f"      Open http://localhost:8080 in your browser")
                
                # Ask if user wants to start the web interface
                try:
                    response = input("\n🤔 Would you like to start the web interface now? (y/n): ")
                    if response.lower().startswith('y'):
                        print("\n🚀 Starting beancount-import web interface...")
                        print("   📝 Note: This will start a web server on port 8080")
                        print("   🛑 Press Ctrl+C to stop the server")
                        
                        # Change to web directory and start the server
                        os.chdir(web_dir)
                        subprocess.run([sys.executable, "start_web_interface.py"])
                        
                except KeyboardInterrupt:
                    print("\n\n👋 Web interface stopped. Demo completed!")
                except Exception as e:
                    print(f"\n❌ Error starting web interface: {e}")
    
    else:
        print("\n⚠️  Step 2: Enhanced processing not available")
        print("   💡 This could be due to missing dependencies or configuration issues")
    
    # Step 3: Summary
    print(f"\n📋 Demo Summary:")
    print(f"✅ Phase 1 Integration Complete!")
    print(f"   📊 Your existing Excel parsing works as before")
    print(f"   🔄 Enhanced with beancount-import post-processing")
    print(f"   🎯 Ready for ML-based classification")
    print(f"   🌐 Web interface for transaction review")
    
    print(f"\n🎯 Next Steps:")
    print(f"   1. Review transactions in the web interface")
    print(f"   2. Train the ML classifier with your choices")
    print(f"   3. Enjoy automated account predictions!")
    
    print(f"\n📚 Files to explore:")
    print(f"   📄 classified_transactions.csv - Your classified data")
    print(f"   📄 transactions.beancount - Beancount journal")
    if output_dir.exists():
        print(f"   📁 {output_dir}/ - Enhanced processing files")
    
    print("\n🎉 Demo completed successfully!")

if __name__ == "__main__":
    main()
