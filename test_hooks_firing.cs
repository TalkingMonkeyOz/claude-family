// TEST FILE - To verify if csharp.instructions.md auto-applies
// If hooks are working, I should see C# coding standards in context
// TEST 4: After fixing stdin-first logic

namespace TestHooks
{
    public class TestClass
    {
        public void TestMethod()
        {
            // Testing if hook now reads from stdin correctly
            var x = 1;
            var y = 2;
            var z = 3;
            var w = 4; // Fourth test - stdin-first fix
        }
    }
}
