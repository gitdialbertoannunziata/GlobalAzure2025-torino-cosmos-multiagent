using System;

namespace CosmosEmbeddingGenerator;

public class CosmosEmbeddingOptions
{
    public string OpenAiEndpoint { get; set; } = string.Empty;
    public string OpenAiDeploymentName { get; set; } = string.Empty;
    public int OpenAiDimensions { get; set; } = 1536;
    public string VectorProperty { get; set; } = string.Empty;
    public string HashProperty { get; set; } = string.Empty;

    public string OpenAiApiKey { get; set; } = string.Empty;
    public List<string> PropertiesToEmbed { get; set; } = [
      "product_name",
      "description",
      "category"
    ];
}
